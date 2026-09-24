/**
 * Odoo 19 port.
 * 18 da chek `props.data.orderlines` (matnli ma'lumot) bilan ishlardi.
 * 19 da `props.order` — haqiqiy buyurtma obyekti, shuning uchun summalar
 * matndan ajratilmaydi, to'g'ridan-to'g'ri olinadi.
 */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

const DISCOUNT_NAMES = ["discount", "скидка", "chegirma"];

patch(OrderReceipt.prototype, {
    /** Bu qator chegirma (mukofot) qatorimi? */
    isDiscountRewardLine(line) {
        if (!line || !line.is_reward_line) {
            return false;
        }
        // Asosiy mezon — mukofot turi (nomga bog'liq emas)
        const rewardType = line.reward_id?.reward_type;
        if (rewardType) {
            return rewardType === "discount";
        }
        // Zaxira mezon: mahsulot nomi
        const name = (line.full_product_name || line.product_id?.name || "")
            .toString()
            .toLowerCase();
        return DISCOUNT_NAMES.some((n) => name.includes(n));
    },

    /** Chekda ko'rsatiladigan umumiy chegirma. Bo'lmasa — false. */
    get customTotalDiscount() {
        const order = this.order;
        if (!order) {
            return false;
        }
        let total = 0;
        try {
            total += order.getTotalDiscount() || 0;
        } catch {
            total += 0;
        }
        for (const line of order.lines || []) {
            if (this.isDiscountRewardLine(line)) {
                total += Math.abs(line.displayPrice || 0);
            }
        }
        total = order.currency.round(total);
        return total ? this.formatCurrency(total) : false;
    },
});
