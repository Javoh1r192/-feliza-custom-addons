# -*- coding: utf-8 -*-
"""
AVTOMATIK ANIQLASH QATLAMI
==========================
Modul o'rnatilgan bazada qaysi maydonlar mavjudligini o'zi tekshiradi va
mavjudlariga moslashadi. Shu sabab modul hech qanday custom modulga
bog'liq emas — ular bo'lsa qo'shimcha imkoniyat beradi, bo'lmasa panel
baribir ishlaydi.

Natija bir marta hisoblanib, registry darajasida keshlanadi
(tools.ormcache) — har bir so'rovda qayta tekshirilmaydi.
"""
from odoo import api, models
from odoo.tools import ormcache


# --------------------------------------------------------------------- #
#  SOTUVCHI va KASSIR — bu IKKI BOSHQA odam                              #
#
#  Odoo'ning o'zida POS'da faqat KASSIR bor: `pos.order.employee_id`,
#  uning yorlig'i ham «Cashier». Chekni kim urgani shu yerga yoziladi.
#
#  Kim SOTGANI esa Odoo'da yo'q — u alohida custom modul bilan qo'shiladi
#  (Feliza'da `pos.order.salesperson_emp_id`, yorlig'i «Sotuvchi»).
#
#  Shuning uchun sotuvchini qidirganda kassir maydoniga TUSHIB QOLMASLIK
#  kerak: avval custom maydonlar, keyin yorlig'i bo'yicha qidiruv, va faqat
#  eng oxirida — hech narsa topilmasa — kassir maydoni zaxira sifatida
#  (bu holatda `is_fallback` bayrog'i qo'yiladi va panelda ogohlantiriladi).
# --------------------------------------------------------------------- #

# 1-bosqich: aniq nomlar (custom modullar shu nomlarni ishlatadi)
SALESPERSON_CANDIDATES = [
    ("pos.order.line", "salesperson_emp_id"),
    ("pos.order.line", "salesperson_id"),
    ("pos.order.line", "sotuvchi_id"),
    ("pos.order.line", "seller_id"),
    ("pos.order.line", "sales_person_id"),
    ("pos.order.line", "sales_employee_id"),
    ("pos.order", "salesperson_emp_id"),
    ("pos.order", "salesperson_id"),
    ("pos.order", "sotuvchi_id"),
    ("pos.order", "seller_id"),
    ("pos.order", "sales_person_id"),
    ("pos.order", "sales_employee_id"),
]

# 2-bosqich: maydon YORLIG'I bo'yicha qidiruv (nomi boshqacha bo'lsa ham)
SALESPERSON_LABELS = ["sotuvchi", "продавец", "salesperson", "sales person",
                      "sales rep", "seller"]

# Kassirga tegishli so'zlar — sotuvchi deb olinmasligi uchun
CASHIER_LABELS = ["kassir", "кассир", "cashier", "касса"]

# 3-bosqich: zaxira (sotuvchi maydoni umuman bo'lmasa)
SALESPERSON_FALLBACK = [
    ("pos.order", "employee_id"),
    ("pos.order", "user_id"),
]

# Kassir maydoni — sotuvchidan ALOHIDA bo'lishi kerak.
# `employee_id` birinchi: Odoo 19'da aynan shu kassir.
CASHIER_CANDIDATES = [
    ("pos.order", "employee_id"),
    ("pos.order", "cashier_id"),
    ("pos.order", "user_id"),
]

PERSON_MODELS = ("hr.employee", "res.users", "res.partner")

# O'lcham atributi nomlari (kichik harfda qidiriladi)
SIZE_ATTR_KEYWORDS = ["o'lcham", "olcham", "размер", "size", "razmer", "razmer"]
COLOR_ATTR_KEYWORDS = ["rang", "цвет", "color", "colour"]


class FelizaDetect(models.AbstractModel):
    """Bazadagi mavjud maydonlarni aniqlaydigan yordamchi model."""

    _name = "feliza.detect"
    _description = "Feliza Dashboard — avtomatik aniqlash"

    # ------------------------------------------------------------------ #
    #  Asosiy aniqlash                                                     #
    # ------------------------------------------------------------------ #
    @api.model
    @ormcache()
    def _detect(self):
        """Bazani tekshirib, moslashuv xaritasini qaytaradi.

        ormcache tufayli bu bir marta hisoblanadi. Modul yangilanganda
        yoki server qayta ishga tushganda kesh tozalanadi.
        """
        env = self.env

        def has_model(name):
            return name in env

        def has_field(model, field):
            return has_model(model) and field in env[model]._fields

        def has_column(table, column):
            """Bazada USTUN bormi.

            `has_field` faqat Python modelini ko'radi. Agar modul fayllari
            yangilangan-u, `-u` bilan yangilanmagan bo'lsa, maydon bor
            ko'rinadi, lekin ustun hali yaratilmagan bo'ladi — SQL esa
            "column does not exist" deb yiqiladi. Shuning uchun SQL
            ishlatadigan maydonlar aynan shu yerdan tekshiriladi.
            """
            env.cr.execute("""
                SELECT 1 FROM information_schema.columns
                 WHERE table_name = %s AND column_name = %s
            """, (table, column))
            return bool(env.cr.fetchone())

        result = {}

        # --- sotuvchi ---
        def person_field(model, field):
            """Maydon odamga ishora qiluvchi many2one bo'lsa — ta'rifini beradi."""
            if not has_field(model, field):
                return None
            f = env[model]._fields[field]
            if f.type != "many2one" or f.comodel_name not in PERSON_MODELS:
                return None
            if not f.store:
                return None          # SQL bilan o'qiymiz — ustun bo'lishi shart
            return {
                "model": model,
                "field": field,
                "comodel": f.comodel_name,
                "label": f.string or field,
                "on_line": model == "pos.order.line",
                "is_fallback": False,
            }

        def label_of(model, field):
            f = env[model]._fields[field]
            return (f.string or field).strip().lower()

        result["salesperson"] = None

        # 1) aniq nomlar
        for model, field in SALESPERSON_CANDIDATES:
            got = person_field(model, field)
            if got:
                result["salesperson"] = got
                break

        # 2) yorlig'i «Sotuvchi»ga o'xshagan har qanday maydon
        if not result["salesperson"]:
            for model in ("pos.order.line", "pos.order"):
                if not has_model(model):
                    continue
                for field in sorted(env[model]._fields):
                    got = person_field(model, field)
                    if not got:
                        continue
                    lbl = label_of(model, field)
                    if any(k in lbl for k in CASHIER_LABELS):
                        continue
                    if any(k in lbl for k in SALESPERSON_LABELS):
                        result["salesperson"] = got
                        break
                if result["salesperson"]:
                    break

        # 3) zaxira — sotuvchi maydoni umuman yo'q. Kassir ko'rsatiladi,
        #    lekin panel buni ochiq aytadi (is_fallback).
        if not result["salesperson"]:
            for model, field in SALESPERSON_FALLBACK:
                got = person_field(model, field)
                if got:
                    got["is_fallback"] = True
                    result["salesperson"] = got
                    break

        # --- kassir (sotuvchidan boshqa maydon bo'lsa) ---
        result["cashier"] = None
        sp = result["salesperson"]
        for model, field in CASHIER_CANDIDATES:
            got = person_field(model, field)
            if not got:
                continue
            # sotuvchi bilan bir xil maydon bo'lsa — kassir alohida emas
            if sp and sp["model"] == model and sp["field"] == field:
                continue
            result["cashier"] = got
            break

        # --- chegirma ---
        result["discount"] = has_field("pos.order.line", "discount")

        # --- kassa farqi ---
        result["cash_diff"] = None
        for field in ("cash_register_difference", "cash_real_difference"):
            if has_field("pos.session", field):
                result["cash_diff"] = field
                break

        # --- to'lov turi: naqdmi ---
        result["cash_flag"] = None
        for field in ("is_cash_count", "type"):
            if has_field("pos.payment.method", field):
                result["cash_flag"] = field
                break

        # --- omborlar aro o'tkazma moduli (ixtiyoriy) ---
        result["interwh"] = (
            has_field("stock.move", "interwh_report_status")
            and has_field("stock.picking", "inter_wh_delivery_id")
        )

        # --- kamomat (warehouse_transfer_custom_19v 1.5+) ---
        # DIQQAT: bu yerda maydon emas, aynan USTUN tekshiriladi — modul
        # fayllari yangi, lekin baza yangilanmagan holatda bo'lim ochilib
        # SQL xatosi bermasligi uchun.
        result["kamomat"] = (
            has_column("stock_move", "feliza_kamomat")
            and has_column("stock_move", "feliza_kamomat_shop_id")
            and has_column("stock_move", "feliza_kamomat_delivery_id")
            and has_column("stock_picking", "feliza_kamomat_receipt_id")
            and has_column("stock_picking", "warehouse_id")
        )
        # 1.6 dan: aniq kamomat miqdori. 1.5 da yo'q — o'shanda
        # `product_uom_qty` ishlatiladi.
        result["kamomat_qty"] = (
            result["kamomat"]
            and has_column("stock_move", "feliza_kamomat_qty")
        )

        # --- o'lcham / rang atributlari ---
        result["size_attr_id"] = self._find_attribute(SIZE_ATTR_KEYWORDS)
        result["color_attr_id"] = self._find_attribute(COLOR_ATTR_KEYWORDS)

        # --- do'kon guruhlash maydoni (shu modul qo'shadi) ---
        result["store_group"] = has_field("pos.config", "feliza_store_group")

        return result

    @api.model
    def _find_attribute(self, keywords):
        """Nomi kalit so'zlarga mos keladigan product.attribute ni topadi."""
        if "product.attribute" not in self.env:
            return None
        for attr in self.env["product.attribute"].sudo().search([]):
            name = (attr.name or "").strip().lower()
            if any(k in name for k in keywords):
                return attr.id
        return None

    # ------------------------------------------------------------------ #
    #  Qulay yordamchilar                                                  #
    # ------------------------------------------------------------------ #
    @api.model
    def salesperson_info(self):
        return self._detect().get("salesperson")

    @api.model
    def cashier_info(self):
        return self._detect().get("cashier")

    @api.model
    def has_discount(self):
        return self._detect().get("discount", False)

    @api.model
    def cash_diff_field(self):
        return self._detect().get("cash_diff")

    @api.model
    def size_attribute_id(self):
        return self._detect().get("size_attr_id")

    @api.model
    def has_interwh(self):
        return self._detect().get("interwh", False)

    @api.model
    def has_kamomat(self):
        return self._detect().get("kamomat", False)

    @api.model
    def has_kamomat_qty(self):
        """1.6 dagi aniq miqdor ustuni bormi."""
        return self._detect().get("kamomat_qty", False)

    # ------------------------------------------------------------------ #
    #  Diagnostika — foydalanuvchi ko'rishi uchun                          #
    # ------------------------------------------------------------------ #
    @api.model
    def diagnostics(self):
        """Sozlamalar sahifasida ko'rsatiladigan hisobot.

        Har bir bo'lim ishlashi uchun nima topilgani/topilmagani.
        """
        d = self._detect()
        rows = []

        sp = d.get("salesperson")
        rows.append({
            "key": "Sotuvchi maydoni",
            "ok": bool(sp) and not sp.get("is_fallback"),
            "value": ("%s.%s (%s) → %s"
                      % (sp["model"], sp["field"], sp.get("label") or "",
                         sp["comodel"]))
                     if sp else "topilmadi",
            "note": ("«Xodimlar» bo'limi shu maydonga tayanadi."
                     if sp and not sp.get("is_fallback") else
                     "Sotuvchi maydoni topilmadi — vaqtincha KASSIR "
                     "ko'rsatilyapti. Sotuvchini yozadigan modul o'rnatilsa, "
                     "panel avtomat o'sha maydonga o'tadi."
                     if sp else
                     "«Xodimlar» bo'limi ishlamaydi. POS'da sotuvchi "
                     "yozilmayotgan bo'lishi mumkin."),
        })

        ca = d.get("cashier")
        rows.append({
            "key": "Kassir maydoni",
            "ok": bool(ca),
            "value": ("%s.%s" % (ca["model"], ca["field"])) if ca else "alohida emas",
            "note": ("Kassir va sotuvchi alohida baholanadi."
                     if ca else
                     "Kassir sotuvchi bilan bir xil maydonda — alohida "
                     "baholash mumkin emas."),
        })

        rows.append({
            "key": "Chegirma",
            "ok": d.get("discount"),
            "value": "pos.order.line.discount" if d.get("discount") else "topilmadi",
            "note": "Chegirma ko'rsatkichlari hisoblanadi."
                    if d.get("discount") else "Chegirma ustunlari bo'sh qoladi.",
        })

        cd = d.get("cash_diff")
        rows.append({
            "key": "Kassa farqi",
            "ok": bool(cd),
            "value": ("pos.session.%s" % cd) if cd else "topilmadi",
            "note": "Kassirlar aniqligi kuzatiladi."
                    if cd else "Kassa farqi ko'rsatilmaydi.",
        })

        sa = d.get("size_attr_id")
        attr_name = ""
        if sa:
            attr_name = self.env["product.attribute"].sudo().browse(sa).name
        rows.append({
            "key": "O'lcham atributi",
            "ok": bool(sa),
            "value": ("«%s» (id=%s)" % (attr_name, sa)) if sa else "topilmadi",
            "note": "O'lcham egri chizig'i ishlaydi."
                    if sa else
                    "O'lcham tahlili ko'rsatilmaydi. Atribut nomida "
                    "«o'lcham» yoki «размер» so'zi bo'lishi kerak.",
        })

        rows.append({
            "key": "Omborlar aro o'tkazma",
            "ok": d.get("interwh"),
            "value": "warehouse_transfer_custom_19v topildi"
                     if d.get("interwh") else "o'rnatilmagan",
            "note": "Yo'ldagi o'tkazmalar ko'rsatiladi."
                    if d.get("interwh") else "Bu bo'lim bo'sh qoladi.",
        })

        rows.append({
            "key": "Kamomat",
            "ok": d.get("kamomat"),
            "value": ("warehouse_transfer_custom_19v %s topildi"
                      % ("1.6+" if d.get("kamomat_qty") else "1.5"))
                     if d.get("kamomat") else "eski versiya yoki yo'q",
            "note": ("Do'konga kam yetib borgan yuklar ko'rsatiladi."
                     if d.get("kamomat_qty") else
                     "Ishlaydi, lekin modul 1.5 — skladchi kamomatning "
                     "bir qismini qabul qilsa hisobotdagi son o'zgarib "
                     "ketishi mumkin. 1.6 ga yangilash tavsiya etiladi.")
                    if d.get("kamomat")
                    else "«Kamomat» bo'limi ko'rinmaydi. Modulni 1.5 "
                         "yoki undan yangi versiyaga yangilang "
                         "(fayl nusxalash yetarli emas — `-u` bilan "
                         "yangilash kerak).",
        })

        # reja
        target_count = self.env["feliza.sales.target"].sudo().search_count([])
        rows.append({
            "key": "Savdo rejasi",
            "ok": target_count > 0,
            "value": "%s ta yozuv" % target_count,
            "note": "Reja bajarilishi hisoblanadi."
                    if target_count else
                    "Reja kiritilmagan — «Dashboard > Reja» bo'limida kiriting. "
                    "Reja bo'lmasa, foiz o'rniga «—» ko'rsatiladi.",
        })

        return rows
