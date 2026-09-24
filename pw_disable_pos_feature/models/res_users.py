# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    pw_disable_payment = fields.Boolean("To'lov qilishni yopish", default=False, copy=False)
    pw_disable_discount = fields.Boolean("Chegirmani berishni yopish", default=False, copy=False)
    pw_disable_products = fields.Boolean("Mahsulot tanlashni yopish", default=False, copy=False)
    pw_disable_qty = fields.Boolean("Mahsulot sonini o'zgartirishni yopish", default=False, copy=False)
    pw_disable_price = fields.Boolean("Narxni o'zgartirishni yopish", default=False, copy=False)
    pw_disable_remove_orderline = fields.Boolean("Tanlangan mahsulotni o'chirishni yopish", default=False, copy=False)
    pw_disable_customer_account = fields.Boolean("Qarzga sotishni yopish", default=False, copy=False)
    pw_disable_closeregister = fields.Boolean("Kassani ochib-yopishni o'chirish", default=False, copy=False)
    pw_disable_cashinout = fields.Boolean("Pul berish/qabul qilishni o'chirish", default=False, copy=False)
    pw_disable_refund = fields.Boolean("qaytarib berish o'chirish", default=False, copy=False)
