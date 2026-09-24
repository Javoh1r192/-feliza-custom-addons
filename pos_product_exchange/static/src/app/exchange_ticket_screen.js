/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

/**
 * "Mahsulot almashtirish" (Product Exchange).
 *
 * IMPORTANT (read before changing this file): Odoo 19's POS frontend
 * deliberately does not allow adding a new, positive-quantity sale line to
 * a refund order - see `PosOrder.isSaleDisallowed()` in
 * point_of_sale/static/src/app/models/pos_order.js - and it also requires
 * a refund order's payment to be validated before the cashier can move on
 * to something else (leaving that screen early triggers Odoo's own
 * "you must confirm the return" warning). Because of this intentional,
 * hard restriction, a "return + new sale in one single order/payment" is
 * not something Odoo 19 supports, and trying to force it (e.g. by
 * redirecting away from the payment screen) fights core safeguards that
 * exist to keep returns properly tracked for accounting.
 *
 * This button is therefore a clearly-labeled trigger for Odoo's own,
 * completely UNMODIFIED refund flow - it just calls `onDoRefund()`
 * directly, so it behaves exactly like the native "Refund" button
 * (same validations, same payment screen, same everything). The intended
 * cashier workflow for an exchange is two native, fully-supported steps:
 *   1. Press "Almashtirish" -> validate the return payment, same as a
 *      normal refund.
 *   2. Press "New Order" and ring up the replacement product as a normal
 *      sale.
 * The `is_exchange` field (see models/pos_order.py) lets these orders be
 * filtered under a business-friendly label in the backend afterwards.
 *
 * Because this only ever calls the native method as-is, it can never
 * conflict with any other module that also patches/extends `onDoRefund`
 * or `TicketScreen`.
 */
patch(TicketScreen.prototype, {
    async onDoExchange() {
        return this.onDoRefund();
    },
});
