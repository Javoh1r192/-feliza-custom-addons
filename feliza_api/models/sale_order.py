from odoo import models, fields
import uuid

import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    web_order_id = fields.Char(
        string="WEB Order ID",
        default=lambda self: str(uuid.uuid4()),
        copy=False,
        readonly=True,
    )

    order_number = fields.Char(string="Order Number")
    delivery_address = fields.Char(string="Delivery Address")
    delivery_method = fields.Selection([
        ("courier", "Courier"),
        ("pickup", "Pickup"),
        ("branch_pickup", "Branch Pickup"),
    ], string="Delivery Method")
    delivery_fee = fields.Float(string="Delivery Fee")
    web_order_created = fields.Datetime(string="WEB Order created")

    payment_method    = fields.Selection([
        ("payme", "Payme"),
        ("click", "Click"),
        ("uzum", "Uzum"),
        ("cod", "Cash on Delivery"),
    ], string="Payment Method")
    payment_status    = fields.Selection([
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ], string="Payment type")
    payment_txn_id    = fields.Char(string="Payment TXN ID")


    def _get_reward_values_discount(self, reward, coupon, **kwargs):
        vals = super()._get_reward_values_discount(reward, coupon, **kwargs)

        cashback_used = self.env.context.get("cashback_used_points")

        if cashback_used:
            for line in vals:
                if line.get("points_cost", 0):
                    line["points_cost"] = cashback_used

        return vals