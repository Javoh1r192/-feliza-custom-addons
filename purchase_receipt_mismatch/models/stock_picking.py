import logging
from odoo import models, _

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if (picking.state == 'done'
                    and picking.picking_type_code == 'incoming'
                    and picking.purchase_id):
                self._check_quantity_mismatch(picking)
        return res

    def _check_quantity_mismatch(self, picking):
        mismatches = []
        for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
            ordered = move.product_uom_qty
            done = move.quantity
            if abs(ordered - done) > 0.001:
                diff = done - ordered
                sign = "🔼 ko'p" if diff > 0 else "🔽 kam"
                mismatches.append(
                    f"• <b>{move.product_id.display_name}</b>: "
                    f"buyurtma <b>{ordered:.0f}</b>, "
                    f"qabul <b>{done:.0f}</b> "
                    f"({abs(diff):.0f} ta {sign})"
                )

        if not mismatches:
            return

        po = picking.purchase_id
        body = (
            f"⚠️ <b>Miqdor farqi aniqlandi</b> ({picking.name}):<br/>"
            + "<br/>".join(mismatches)
        )

        # PO chatteriga yozamiz
        po.message_post(
            body=body,
            subject=_("Miqdor farqi: %s") % po.name,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        # Sozlamadan tanlangan foydalanuvchiga activity yuboramiz
        notify_user_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'purchase_receipt_mismatch.notify_user_id', 0
            )
        )
        if notify_user_id:
            user = self.env['res.users'].browse(notify_user_id)
            if user.exists():
                po.activity_schedule(
                    'mail.mail_activity_data_warning',
                    user_id=user.id,
                    summary=_("Miqdor farqi: %s") % po.name,
                    note=body,
                )
                _logger.info(
                    "Miqdor farqi xabari yuborildi → PO: %s | User: %s",
                    po.name, user.name,
                )
