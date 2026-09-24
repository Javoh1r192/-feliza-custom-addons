import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

function isGiftCardRewardLine(line) {
    return Boolean(
        line &&
            line.is_reward_line &&
            line.coupon_id &&
            line.reward_id?.program_id?.program_type === "gift_card"
    );
}

patch(OrderSummary.prototype, {
    /**
     * pos_loyalty reward qatorlarida narx o'zgartirishni bloklaydi.
     * Gift card reward qatori uchun "Price" rejimida kiritilgan qiymatni
     * o'zimiz qayta ishlaymiz (super chaqirilmaydi).
     */
    _setValue(val) {
        const selectedLine = this.currentOrder.getSelectedOrderline();
        if (isGiftCardRewardLine(selectedLine)) {
            if (val === "remove") {
                // qator olib tashlanganda kassir kiritgan summani ham unutamiz
                this.currentOrder.setGiftCardManualAmount(selectedLine.coupon_id.id, undefined);
            } else if (this.pos.numpadMode === "price" && val !== "") {
                this.setLinePrice(selectedLine, val);
                return;
            }
        }
        return super._setValue(...arguments);
    },

    /**
     * Ham numpad orqali, ham "price control" popup'i orqali shu yerga keladi.
     */
    async setLinePrice(line, price) {
        if (!isGiftCardRewardLine(line)) {
            return super.setLinePrice(...arguments);
        }
        const order = this.currentOrder;
        const couponId = line.coupon_id.id;
        const amount = Math.abs(parseFloat(price));
        if (isNaN(amount)) {
            return;
        }
        const { balance, discountable } = order.getGiftCardMaxUsable(couponId, line.reward_id);
        const fmt = (v) => this.env.utils.formatCurrency(v);

        if (amount > balance + 0.005) {
            this.numberBuffer.reset();
            this.dialog.add(AlertDialog, {
                title: _t("Vaucher balansi yetarli emas"),
                body: _t(
                    "Vaucher qoldig'i: %s. Undan ko'p summa kiritib bo'lmaydi.",
                    fmt(balance)
                ),
            });
            return;
        }
        if (amount > discountable + 0.005) {
            this.numberBuffer.reset();
            this.dialog.add(AlertDialog, {
                title: _t("Summa order'dan katta"),
                body: _t(
                    "Order summasi: %s. Vaucherdan undan ko'p yechib bo'lmaydi.",
                    fmt(discountable)
                ),
            });
            return;
        }
        if (amount === 0) {
            // 0 = qo'lda cheklov yo'q, standart (to'liq) hisoblashga qaytamiz
            order.setGiftCardManualAmount(couponId, undefined);
        } else {
            order.setGiftCardManualAmount(couponId, amount);
        }
        // Reward qatorlari qayta hisoblanadi; tanlov PosOrder._updateRewardLines
        // patch'i orqali saqlanadi.
        this.pos.updateRewards();
    },
});
