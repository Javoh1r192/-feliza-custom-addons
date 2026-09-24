# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrder(models.Model):
    """Add a business-friendly Almashtirish (Exchange) label/filter for
    reporting purposes only.

    Design note (important): Odoo 19's POS frontend deliberately does NOT
    allow a refund/return order to also contain a new, positive-quantity
    sale line - see PosOrder.isSaleDisallowed() in
    point_of_sale/static/src/app/models/pos_order.js, which explicitly
    blocks adding a positive-qty line to an order where is_refund is
    true. The POS also requires a refund order's payment to be validated
    before the cashier can move on. Because of this hard, intentional
    core restriction, an exchange cannot be a single combined order or
    payment - it is implemented as two separate, fully native
    transactions:
      1. A normal return, created and validated exactly like Odoo's
         built-in Refund, via the Almashtirish button.
      2. A regular new order for the replacement product, created the
         normal way (native New Order button).

    This field is a read-only, server-side COMPUTED alias of the
    already-existing is_refund field, so orders created via the
    Almashtirish button can still be filtered under a business-friendly
    label in the backend Orders list/reports. It does not add any new
    field to the list of data synced to the POS frontend
    (_load_pos_data_fields is left untouched), so it cannot affect the
    POS frontend order model in any way.
    """

    _inherit = "pos.order"

    is_exchange = fields.Boolean(
        string="Mahsulot almashtirish",
        compute="_compute_is_exchange",
        store=True,
        help=(
            "Ushbu buyurtma kassadagi Almashtirish tugmasi orqali "
            "yaratilgan qaytarish (return) buyurtmasi. Texnik jihatdan bu "
            "oddiy qaytarish bilan bir xil (Odoo bitta buyurtmada "
            "qaytarish va yangi sotuvni birlashtirishga yol qoymaydi); "
            "ushbu maydon faqat hisobotlarda qulay nom bilan filtrlash "
            "uchun ishlatiladi."
        ),
    )

    @api.depends("is_refund")
    def _compute_is_exchange(self):
        for order in self:
            order.is_exchange = order.is_refund
