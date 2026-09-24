# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Online order = ombori "Online" so'zli (Online Ombor / Feliza Online Ombor)
    x_is_online = fields.Boolean("Online sotuv", compute='_compute_x_is_online')

    @api.depends('warehouse_id', 'warehouse_id.name')
    def _compute_x_is_online(self):
        for order in self:
            name = (order.warehouse_id.name or '').lower()
            order.x_is_online = 'online' in name

    def action_confirm_and_pay(self):
        """Online sotuv tez-oqimi: tasdiqlash -> invoys(yaratib post) ->
        To'lov (Register Payment) oynasi. Yetkazish (stock) avto QILINMAYDI —
        action_confirm yetkazish hujjatini yaratadi (lekin tasdiqlanmaydi,
        astatka kamaymaydi). To'lovdan keyin shu order oynasida qoladi."""
        self.ensure_one()
        if not self.order_line:
            raise UserError(_("Sotuvda tovar yo'q."))
        if (self.amount_total or 0.0) <= 0:
            raise UserError(_("Sotuvda to'lanadigan summa yo'q (0 so'm). "
                              "Tovar va uning narxini qo'shing."))
        # 1) tasdiqlash
        if self.state in ('draft', 'sent'):
            self.action_confirm()
        # 2) invoys — mavjud bo'lmasa yaratamiz (dublikat yaratmaymiz)
        inv = self.invoice_ids.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state != 'cancel')
        if not inv:
            inv = self._create_invoices()
        inv = inv[:1]
        if not inv:
            raise UserError(_("Invoys yaratilmadi (invoys siyosati?)."))
        # 3) book (post)
        if inv.state == 'draft':
            inv.action_post()
        # 4) To'lov oynasi (jurnal: Naqd/Click/UzCard online)
        return {
            'name': _("To'lov"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': inv.ids,
            },
        }
