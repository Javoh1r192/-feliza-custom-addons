import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    receipt_mismatch = fields.Selection(
        [
            ('ok', "To'liq qabul"),
            ('less', 'Kam qabul'),
            ('more', "Ko'p qabul"),
            ('mixed', 'Aralash farq'),
        ],
        string='Qabul holati',
        compute='_compute_receipt_mismatch',
        store=True,
    )

    @api.depends(
        'picking_ids.state',
        'picking_ids.move_ids.product_uom_qty',
        'picking_ids.move_ids.quantity',
    )
    def _compute_receipt_mismatch(self):
        for order in self:
            done_pickings = order.picking_ids.filtered(
                lambda p: p.state == 'done' and p.picking_type_code == 'incoming'
            )
            if not done_pickings:
                order.receipt_mismatch = False
                continue

            has_less = False
            has_more = False
            for picking in done_pickings:
                for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
                    diff = move.quantity - move.product_uom_qty
                    if diff < -0.001:
                        has_less = True
                    elif diff > 0.001:
                        has_more = True

            if has_less and has_more:
                order.receipt_mismatch = 'mixed'
            elif has_less:
                order.receipt_mismatch = 'less'
            elif has_more:
                order.receipt_mismatch = 'more'
            else:
                order.receipt_mismatch = 'ok'
