from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        result = super().action_pos_order_paid()
        for order in self:
            if order.partner_id:
                try:
                    order.partner_id.sudo().write({
                        'x_last_purchase': fields.Datetime.now()
                    })
                    _logger.info("Oxirgi xarid: %s → %s", order.partner_id.name, fields.Datetime.now())
                except Exception as e:
                    _logger.warning("x_last_purchase xato: %s", e)
        return result
