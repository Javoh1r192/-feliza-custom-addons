# -*- coding: utf-8 -*-
"""ARTIKUL VA BARKOD NAVBATI

Feliza'da artikul va barkod ketma-ket beriladi. Bu yerda o'sha ketma-ketlik
saqlanadi va navbatdagi bo'sh raqam topiladi.

MUHIM UCHTA QOIDA (buyurtmachi talabi):
  1. Artikul — MAHSULOTGA bitta. Nechta variant yaratilsa ham bitta artikul.
  2. Barkod — HAR BIR VARIANTGA alohida.
  3. Navbatdagi raqam allaqachon bandmi — xatolik BERMAYDI, keyingisiga
     o'tadi. Mavjud tovarga yangi raqam berilmaydi.

Nega `ir.sequence` emas? Chunki bizga «band bo'lsa o'tkazib yuborish»
kerak, `ir.sequence` esa bandlikni bilmaydi. Shuning uchun raqam
`ir.config_parameter` da turadi va o'qishdan oldin qatori SQL bilan
bloklanadi (`FOR UPDATE`) — ikki xodim bir vaqtda mahsulot yaratsa ham
bir xil raqam ikki marta berilmaydi.
"""
from odoo import _, api, models
from odoo.exceptions import UserError

# Sozlamalardagi kalitlar
PARAM_ARTIKUL = "feliza.birka.last_artikul"
PARAM_BARCODE = "feliza.birka.last_barcode"

# Avto berishni yoqish/o'chirish
PARAM_AUTO_ARTIKUL = "feliza.birka.auto_artikul"
PARAM_AUTO_BARCODE = "feliza.birka.auto_barcode"


def auto_on(env, key):
    """Avto berish yoqilganmi?

    Parametr umuman yo'q bo'lsa — YOQILGAN deb hisoblanadi. Bu modul
    o'rnatilgandan keyin darhol ishlashi uchun kerak; keyin xodim
    sozlamalardan o'chirsa, «False» yozib qo'yiladi.
    """
    raw = env["ir.config_parameter"].sudo().get_param(key)
    if raw is None or raw is False or str(raw).strip() == "":
        return True
    return str(raw).strip().lower() not in ("0", "false", "no")

# Bir martada tekshiriladigan nomzodlar soni. Bittalab tekshirish sekin —
# bazada 12 mingdan ortiq tovar bor, band raqamlar ketma-ket kelishi mumkin.
CHUNK = 300
MAX_TRIES = 200      # ya'ni 60 000 raqamgacha qidiradi, keyin to'xtaydi

# Feliza artikuli — 6 xonali (100014 ... 800020). Bazadagi 4394 ta
# artikulning hammasi shunday. Shundan kichik raqam (masalan «3»)
# xato kiritilgan degani: undan «4» kabi artikul chiqib ketmasligi
# kerak. Shuning uchun quyidagi chegara.
MIN_ARTIKUL = 100000


def ean13_check_digit(base12):
    """EAN-13 nazorat raqamini hisoblaydi.

    Feliza barkodlari haqiqiy EAN-13: 2000000115535 dagi oxirgi «5» —
    nazorat raqami. Uni noto'g'ri qo'ysak skaner o'qimaydi.
    """
    s = str(base12).rjust(12, "0")[-12:]
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(s))
    return str((10 - total % 10) % 10)


def make_ean13(base12):
    s = str(base12).rjust(12, "0")[-12:]
    return s + ean13_check_digit(s)


class FelizaNumbering(models.AbstractModel):
    _name = "feliza.numbering"
    _description = "Feliza — artikul va barkod navbati"

    # ------------------------------------------------------------------ #
    #  Parametrni bloklab o'qish                                          #
    # ------------------------------------------------------------------ #
    @api.model
    def _lock_param(self, key, default=""):
        ICP = self.env["ir.config_parameter"].sudo()
        param = ICP.search([("key", "=", key)], limit=1)
        if not param:
            ICP.set_param(key, default)
            param = ICP.search([("key", "=", key)], limit=1)
        # qatorni bloklaymiz — tranzaksiya tugaguncha boshqa hech kim
        # bu raqamni o'qib, o'zgartira olmaydi
        self.env.cr.execute(
            "SELECT value FROM ir_config_parameter WHERE id = %s FOR UPDATE",
            (param.id,))
        row = self.env.cr.fetchone()
        return param, (row[0] if row else default)

    @api.model
    def _write_param(self, param, value):
        self.env.cr.execute(
            "UPDATE ir_config_parameter SET value = %s WHERE id = %s",
            (str(value), param.id))
        param.invalidate_recordset(["value"])

    # ------------------------------------------------------------------ #
    #  ARTIKUL                                                            #
    # ------------------------------------------------------------------ #
    @api.model
    def next_artikul(self, categ=None):
        """Bo'sh artikul qaytaradi va navbatni surib qo'yadi.

        `categ` berilsa — o'sha kategoriyaga biriktirilgan SERIYADAN
        (masalan sumka 6xxxxx, atir 4xxxxx). Seriya topilmasa yoki
        kategoriya berilmasa — umumiy navbatdan.
        """
        series = self.env["feliza.artikul.series"].series_for_category(categ) \
            if categ else self.env["feliza.artikul.series"].browse()

        if series:
            return self._next_from_series(series)

        param, raw = self._lock_param(PARAM_ARTIKUL, "0")
        try:
            last = int(str(raw).strip() or 0)
        except ValueError:
            raise UserError(_(
                "Sozlamalardagi «oxirgi artikul» qiymati son emas: %s"
            ) % raw)

        # Seriya topilmadi. Umumiy navbat ham ishonchli bo'lmasa —
        # jim turib «4» kabi noto'g'ri artikul bermaymiz, balki
        # xodimga aniq nima qilish kerakligini aytamiz.
        if last < MIN_ARTIKUL:
            categ_name = (categ.sudo().complete_name or categ.sudo().name
                          ) if categ else False
            if categ_name:
                raise UserError(_(
                    "«%(categ)s» kategoriyasi uchun artikul seriyasi "
                    "topilmadi.\n\n"
                    "Sozlamalar → Ombor → «Artikul seriyalari — kategoriya "
                    "bo'yicha» jadvalidan shu kategoriyani kerakli seriyaga "
                    "qo'shing (masalan kiyim uchun «Kiyim (1xxxxx)»).\n\n"
                    "Eslatma: pastdagi umumiy navbatda «%(raw)s» turibdi — "
                    "bu haqiqiy artikulga o'xshamaydi (Feliza artikuli "
                    "6 xonali), shuning uchun undan foydalanilmadi."
                ) % {"categ": categ_name, "raw": raw})
            raise UserError(_(
                "Mahsulot kategoriyasi ko'rsatilmagan va umumiy artikul "
                "navbati ham to'g'ri sozlanmagan (hozir: «%s»).\n\n"
                "Zakup oynasida kategoriyani tanlang — artikul o'sha "
                "kategoriyaning seriyasidan beriladi."
            ) % raw)

        Tmpl = self.env["product.template"].with_context(
            active_test=False).sudo()
        Prod = self.env["product.product"].with_context(
            active_test=False).sudo()

        n = last
        for _try in range(MAX_TRIES):
            cands = [str(n + i) for i in range(1, CHUNK + 1)]
            taken = set(Tmpl.search([("default_code", "in", cands)])
                        .mapped("default_code"))
            taken |= set(Prod.search([("default_code", "in", cands)])
                         .mapped("default_code"))
            for code in cands:
                if code not in taken:
                    self._write_param(param, int(code))
                    return code
            n += CHUNK
        raise UserError(_("Bo'sh artikul topilmadi (%s dan boshlab).") % last)

    @api.model
    def _next_from_series(self, series):
        """Seriya bo'yicha bo'sh artikul.

        Seriya qatori SQL bilan bloklanadi (`FOR UPDATE`) — ikki xodim
        bir vaqtda bir seriyadan mahsulot yaratsa ham, bir xil raqam
        ikki marta berilmaydi.
        """
        self.env.cr.execute(
            "SELECT last_code FROM feliza_artikul_series WHERE id = %s "
            "FOR UPDATE", (series.id,))
        row = self.env.cr.fetchone()
        raw = "".join(c for c in str(row[0] if row else "") if c.isdigit())
        if not raw:
            raise UserError(_(
                "«%s» seriyasida oxirgi artikul ko'rsatilmagan.") % series.name)
        last = int(raw)

        Tmpl = self.env["product.template"].with_context(
            active_test=False).sudo()
        Prod = self.env["product.product"].with_context(
            active_test=False).sudo()

        n = last
        for _try in range(MAX_TRIES):
            cands = [str(n + i) for i in range(1, CHUNK + 1)]
            taken = set(Tmpl.search([("default_code", "in", cands)])
                        .mapped("default_code"))
            taken |= set(Prod.search([("default_code", "in", cands)])
                         .mapped("default_code"))
            for code in cands:
                if code not in taken:
                    self.env.cr.execute(
                        "UPDATE feliza_artikul_series SET last_code = %s "
                        "WHERE id = %s", (code, series.id))
                    series.invalidate_recordset(["last_code"])
                    return code
            n += CHUNK
        raise UserError(_(
            "«%(s)s» seriyasida bo'sh artikul topilmadi (%(n)s dan boshlab)."
        ) % {"s": series.name, "n": last})

    # ------------------------------------------------------------------ #
    #  BARKOD                                                             #
    # ------------------------------------------------------------------ #
    @api.model
    def next_barcodes(self, count):
        """`count` ta bo'sh EAN-13 barkod qaytaradi."""
        if count <= 0:
            return []
        param, raw = self._lock_param(PARAM_BARCODE, "")
        cur = "".join(ch for ch in str(raw) if ch.isdigit())
        if len(cur) < 12:
            raise UserError(_(
                "Barkod navbati sozlanmagan.\n\n"
                "Sozlamalar → Ombor → «Feliza: artikul va barkod» bo'limida "
                "oxirgi ishlatilgan barkodni (13 xonali) kiriting."))
        base = int(cur[:12])

        Prod = self.env["product.product"].with_context(
            active_test=False).sudo()
        out = []
        offset = 0
        for _try in range(MAX_TRIES):
            chunk = [(base + offset + i, make_ean13(base + offset + i))
                     for i in range(1, CHUNK + 1)]
            taken = set(Prod.search(
                [("barcode", "in", [c for _n, c in chunk])]).mapped("barcode"))
            for num, code in chunk:
                if code in taken:
                    continue
                out.append(code)
                if len(out) >= count:
                    self._write_param(param, code)
                    return out
            offset += CHUNK
        raise UserError(_("Bo'sh barkod topilmadi (%s dan boshlab).") % cur)
