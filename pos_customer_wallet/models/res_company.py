# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pos_wallet_loyalty_program_id = fields.Many2one(
        "loyalty.program",
        string="Cashback Loyalty dasturi",
        domain="[('program_type', '=', 'loyalty'), ('company_id', 'in', (False, id))]",
        help="Odoo'ning o'zining Loyalty (Sodiqlik) dasturlaridan qaysi biri "
        "mijozlarning cashback ballarini to'playdi (masalan, 'Cashback' "
        "nomli, 'Loyalty Cards' turidagi dastur). Mijoz ushbu dasturdagi "
        "ballarni to'plashda hech narsa o'zgarmaydi — bu tamomila Odoo'ning "
        "o'z mexanizmi orqali davom etadi. Ushbu modul faqat shu ballarni "
        "POS'da alohida 'Cashback' TO'LOV USULI orqali (mahsulot sifatida "
        "emas) qisman sarflash imkonini beradi.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        # POS frontend qaysi Loyalty dasturi cashback ekanini bilishi
        # uchun (balans bannerini va overdraft cheklovini hisoblash uchun).
        fields_list = super()._load_pos_data_fields(config)
        return fields_list + ["pos_wallet_loyalty_program_id"]
