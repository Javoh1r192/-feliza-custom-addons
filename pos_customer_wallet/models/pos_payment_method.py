# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    is_wallet_payment = fields.Boolean(
        string="Mijoz hamyoni (Cashback) to'lovi",
        help="Yoqilgan bo'lsa, ushbu to'lov usuli mijozning cashback hamyon "
        "balansidan foydalanadi: POS'da miqdor avtomatik balansdan oshib "
        "ketmaydi, va tasdiqlanganda mijoz balansidan mos summa yechiladi. "
        "Buxgalteriya uchun: bu to'lov usulining jurnali (Journal) va "
        "'Outstanding Account' maydoni Sozlamalar > Mijoz hamyoni bo'limida "
        "belgilangan majburiyat schyotiga (masalan 6930) yo'naltirilgan "
        "bo'lishi tavsiya etiladi — shunda sessiya yopilganda savdo "
        "daromadi qarshisiga avtomatik shu schyot debet qilinadi.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        # POS frontend qaysi to'lov usuli "hamyon" ekanini bilishi uchun.
        fields_list = super()._load_pos_data_fields(config)
        return fields_list + ["is_wallet_payment"]
