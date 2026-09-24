# -*- coding: utf-8 -*-
"""CHEK SARLAVHASI UCHUN MA'LUMOT

Chekning tepasida uchta qator turadi:

    «Feliza» MCHJ XK          <- yuridik nom
    Feliza - Chilonzor        <- do'kon (POS) nomi
    Chilonzor tumani, ...     <- manzil

Uchalasi ham shu yerda tayyorlanadi va POS'ga yuboriladi. Nega
hisoblanadigan maydon? Chunki manzil maydonining nomi bazada
qo'lda qo'shilgan (`x_...`) — u har xil bo'lishi mumkin. Shablonga
maydon nomini yozib qo'ysak, nomi o'zgarganda chek buzilardi.
Bu yerda esa bir nechta nom sinab ko'riladi va topilgani ishlatiladi.
"""
from odoo import api, fields, models

# Manzil maydoni qanday nom bilan qo'shilgan bo'lishi mumkin.
# Ro'yxat tartibi muhim: birinchi topilgani ishlatiladi.
MANZIL_NOMZODLARI = (
    "x_manzil", "x_studio_manzil", "x_studio_manzil_1",
    "x_adres", "x_studio_adres", "x_address", "x_studio_address",
    "manzil", "address", "street",
)

# Yuridik nomni sozlamalardan o'zgartirish mumkin:
#   Sozlamalar -> Texnik -> Tizim parametrlari
PARAM_YURIDIK = "feliza.chek.yuridik_nom"
YURIDIK_SUKUT = "«Feliza» MCHJ XK"


class PosConfig(models.Model):
    _inherit = "pos.config"

    # Do'kon manzili — POS kartochkasida QO'LDA yoziladi va chekning
    # tepasida chiqadi. Har bir do'kon (POS) o'zinikini yozadi.
    feliza_manzil_matn = fields.Char(
        string="Chekdagi manzil",
        help="Chekning tepasida, do'kon nomi ostida chiqadigan manzil. "
             "Bo'sh qolsa kompaniya manzili ishlatiladi.")

    feliza_yuridik = fields.Char(
        string="Chek: yuridik nom", compute="_compute_feliza_chek")
    feliza_dokon = fields.Char(
        string="Chek: do'kon nomi", compute="_compute_feliza_chek")
    feliza_manzil = fields.Char(
        string="Chek: manzil", compute="_compute_feliza_chek")

    @api.depends("name", "company_id", "feliza_manzil_matn")
    def _compute_feliza_chek(self):
        yuridik = self.env["ir.config_parameter"].sudo().get_param(
            PARAM_YURIDIK) or YURIDIK_SUKUT
        for cfg in self:
            cfg.feliza_yuridik = yuridik

            # «Feliza - Chilonzor». Nom allaqachon «Feliza» bilan
            # boshlansa, ikkinchi marta qo'shilmaydi.
            nom = (cfg.name or "").strip()
            if nom.lower().startswith("feliza"):
                cfg.feliza_dokon = nom
            else:
                cfg.feliza_dokon = "Feliza - %s" % nom if nom else "Feliza"

            # manzil: o'z maydonimiz -> qo'lda qo'shilgan maydon ->
            # kompaniya manzili
            manzil = (cfg.feliza_manzil_matn or "").strip()
            for maydon in () if manzil else MANZIL_NOMZODLARI:
                if maydon in cfg._fields:
                    qiymat = cfg[maydon]
                    if qiymat and isinstance(qiymat, str):
                        manzil = qiymat.strip()
                        break
            if not manzil:
                kom = cfg.company_id
                manzil = ", ".join(
                    x for x in (kom.street, kom.street2, kom.city) if x)
            cfg.feliza_manzil = manzil

    # DIQQAT: `pos.config` uchun `_load_pos_data_fields` ni QAYTA
    # YOZMAYMIZ. Odoo bu model uchun bo'sh ro'yxat qaytaradi, bo'sh
    # ro'yxat esa `read()` da «HAMMA maydonni o'qi» degani. Ro'yxatga
    # o'z maydonlarimizni qo'shsak, u uch elementli bo'lib qoladi va
    # POS `currency_id` ni topolmay ishga tushmaydi (sinovda shunday
    # bo'ldi). Hisoblanadigan maydonlarimiz baribir yuklanadi.


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def _load_pos_data_fields(self, config):
        maydonlar = super()._load_pos_data_fields(config)
        # Bo'sh ro'yxat = «hamma maydon». Unga qo'shsak, aksincha,
        # cheklab qo'ygan bo'lardik — shuning uchun tegmaymiz.
        if not maydonlar:
            return maydonlar
        # «Sotuvchi» — `pos_salesperson` moduli qo'shgan maydon.
        # Modul o'rnatilmagan bo'lsa chek baribir ishlaydi.
        if "salesperson_emp_id" in self._fields \
                and "salesperson_emp_id" not in maydonlar:
            maydonlar = maydonlar + ["salesperson_emp_id"]
        return maydonlar
