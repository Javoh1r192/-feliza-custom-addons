# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    feliza_salesperson_id = fields.Many2one(
        'feliza.sale.salesperson', "Sotuvchi (Asosiy)",
        index=True, tracking=True,
        help="Asosiy sotuv sotuvchisi — POS sotuvchisi va tizim "
             "foydalanuvchisidan farqli. KPI hisoblash uchun.")
