/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { getWalletBalance } from "../utils/wallet_utils";

/**
 * Mijoz "Cashback" to'lov usuli bilan balansidan ortiq summa kirita
 * olmasligi kerak. Balans — mijozning Odoo Loyalty kartasidan (native)
 * o'qiladi, hech qanday alohida hamyon maydoni ishlatilmaydi.
 *
 * Bu — YAKUNIY server tomonidagi tekshiruvga (pos_order.py ->
 * _apply_wallet_logic -> res_partner.py -> _wallet_spend) qo'shimcha,
 * faqat tezkor UX uchun: kassir summa kiritishi bilanoq mijoz balansidan
 * oshib ketmasligini ko'radi.
 *
 * Bir buyurtmada bir nechta "wallet" to'lov qatori bo'lishi (kamdan-kam,
 * lekin mumkin) hisobga olingan: har bir qatorning ruxsat etilgan
 * maksimal summasi = mijoz balansi - shu buyurtmadagi BOSHQA wallet
 * qatorlari allaqachon band qilgan summa.
 */
patch(PosPayment.prototype, {
    setAmount(value) {
        const paymentMethod = this.payment_method_id;
        if (paymentMethod && paymentMethod.is_wallet_payment) {
            const order = this.pos_order_id;
            const partner = order && order.partner_id;
            const balance = partner ? getWalletBalance(this.models, partner) : 0;

            const usedByOtherWalletLines = ((order && order.payment_ids) || [])
                .filter(
                    (line) =>
                        line !== this &&
                        line.payment_method_id &&
                        line.payment_method_id.is_wallet_payment
                )
                .reduce((sum, line) => sum + (line.amount || 0), 0);

            const available = Math.max(balance - usedByOtherWalletLines, 0);
            const requested = parseFloat(value) || 0;

            if (requested > available) {
                value = available;
            }
        }
        super.setAmount(value);
    },
});
