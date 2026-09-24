# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    salesperson_emp_id = fields.Many2one(
        'hr.employee',
        string='Sotuvchi',
        help='Savdoni amalga oshirgan sotuvchi (kassirdan farqli bo\'lishi mumkin)',
    )

    def _order_fields(self, ui_order):
        """Client (POS) dan kelgan order ma'lumotlarini server modeliga o'giradi."""
        order_fields = super()._order_fields(ui_order)
        order_fields['salesperson_emp_id'] = ui_order.get('salesperson_emp_id') or False
        return order_fields

    def export_for_ui(self):
        """Server dan client (POS) ga jo'natiladigan ma'lumotlar."""
        result = super().export_for_ui()
        result['salesperson_emp_id'] = (
            {'id': self.salesperson_emp_id.id, 'name': self.salesperson_emp_id.name}
            if self.salesperson_emp_id else False
        )
        return result
