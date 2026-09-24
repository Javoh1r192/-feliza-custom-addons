# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = 'hr.employee'

    pw_disable_payment = fields.Boolean("To'lov qilishni yopish", default=False, copy=False)
    pw_disable_discount = fields.Boolean('Chegirmani berishni yopish', default=False, copy=False)
    pw_disable_products = fields.Boolean('Mahsulot tanlashni yopish', default=False, copy=False)
    pw_disable_qty = fields.Boolean("Mahsulot sonini o'zgartirishni yopish", default=False, copy=False)
    pw_disable_price = fields.Boolean("Narxni o'zgartirishni yopish", default=False, copy=False)
    pw_disable_remove_orderline = fields.Boolean("Tanlangan mahsulotni o'chirishni yopish", default=False, copy=False)
    pw_disable_customer_account = fields.Boolean('Qarzga sotishni yopish', default=False, copy=False)
    pw_disable_closeregister = fields.Boolean("Kassani ochib-yopishni o'chirish", default=False, copy=False)
    pw_disable_cashinout = fields.Boolean("Pul berish/qabul qilishni o'chirish", default=False, copy=False)
    pw_disable_refund = fields.Boolean("qaytarib berish o'chirish", default=False, copy=False)
    pw_disable_pos_numpad_plus_minus = fields.Boolean("Numpad plus/minus tugmasini yopish", default=False, copy=False) 

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list += [
            'pw_disable_payment',
            'pw_disable_discount',
            'pw_disable_products',
            'pw_disable_qty',
            'pw_disable_price',
            'pw_disable_remove_orderline',
            'pw_disable_customer_account',
            'pw_disable_closeregister',
            'pw_disable_cashinout',
            'pw_disable_refund',
            'pw_disable_pos_numpad_plus_minus',
        ]
        return fields_list
