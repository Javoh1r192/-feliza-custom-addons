# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FelizaSaleSalesperson(models.Model):
    """Asosiy (optom) sotuv buyurtmalari uchun ALOHIDA sotuvchilar ro'yxati.

    POS sotuvchilaridan (hr.employee) va tizim foydalanuvchilaridan
    (res.users) mustaqil — qo'lda kiritiladi va boshqariladi. Har sotuvchi
    kartochkasida buyurtmalar soni va jami savdo summasi hisoblanadi (KPI
    uchun asos).
    """
    _name = 'feliza.sale.salesperson'
    _description = "Sotuvchi (asosiy sotuv buyurtmalari uchun)"
    _order = 'name'

    name = fields.Char("Ismi", required=True, index=True)
    phone = fields.Char("Telefon")
    note = fields.Char("Izoh")
    active = fields.Boolean("Faol", default=True)

    currency_id = fields.Many2one(
        'res.currency', "Valyuta",
        default=lambda s: s.env.company.currency_id)
    order_ids = fields.One2many(
        'sale.order', 'feliza_salesperson_id', "Buyurtmalar")
    order_count = fields.Integer(
        "Buyurtmalar (tasdiqlangan)", compute='_compute_stats')
    total_amount = fields.Monetary(
        "Jami savdo", compute='_compute_stats', currency_field='currency_id')

    def _compute_stats(self):
        counts = {}
        sums = {}
        if self.ids:
            Order = self.env['sale.order']
            for sp, cnt, amt in Order._read_group(
                    [('feliza_salesperson_id', 'in', self.ids),
                     ('state', '=', 'sale')],
                    groupby=['feliza_salesperson_id'],
                    aggregates=['__count', 'amount_total:sum']):
                counts[sp.id] = cnt
                sums[sp.id] = amt or 0.0
        for rec in self:
            rec.order_count = counts.get(rec.id, 0)
            rec.total_amount = sums.get(rec.id, 0.0)
