/**
 * Odoo 19 port.
 * 18 -> 19 o'zgarishlar:
 *   @point_of_sale/app/store/pos_store  ->  @point_of_sale/app/services/pos_store
 *   line.get_discount() / set_discount() ->  getDiscount() / setDiscount()
 *   line.get_quantity() / set_quantity() ->  getQuantity() / setQuantity()
 *   this.get_order()                     ->  this.getOrder()
 */
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

// ─── 1. ORDER: foizli chegirmani alohida qator o'rniga tovar qatoriga yozish ───
patch(PosOrder.prototype, {
    _applyReward(reward, coupon_id, args) {
        if (
            reward &&
            reward.reward_type === "discount" &&
            reward.discount_mode === "percent" &&
            !["gift_card", "ewallet"].includes(reward.program_id?.program_type)
        ) {
            return this._applyLoyaltyPercentDiscountToLines(reward);
        }
        return super._applyReward(reward, coupon_id, args);
    },

    _applyLoyaltyPercentDiscountToLines(reward) {
        const discountPercent = reward.discount;
        const applicableProductIds = new Set(
            (reward.all_discount_product_ids || []).map((p) => p.id)
        );

        const regularLines = this.lines.filter((line) => !line.is_reward_line);

        for (const line of regularLines) {
            const productId = line.product_id?.id;
            const shouldApply =
                reward.discount_applicability === "order" ||
                (reward.discount_applicability === "specific" &&
                    applicableProductIds.has(productId));

            if (!shouldApply) {
                continue;
            }
            if (line.getDiscount() === discountPercent) {
                continue;
            }
            line.setDiscount(discountPercent);
        }
        return true;
    },
});

// ─── 2. STORE: mukofot qo'llangandan KEYIN bir xil qatorlarni birlashtirish ───
patch(PosStore.prototype, {
    updateRewards() {
        const result = super.updateRewards(...arguments);

        setTimeout(() => {
            try {
                this._mergeLoyaltyDiscountLines();
            } catch {
                // birlashtirish muvaffaqiyatsiz bo'lsa ham kassa ishlashda davom etadi
            }
        }, 200);

        return result;
    },

    _mergeLoyaltyDiscountLines() {
        const order = this.getOrder();
        if (!order || order.finalized) {
            return;
        }

        const regularLines = order.lines.filter((line) => !line.is_reward_line);
        const merged = new Set();

        for (let i = 0; i < regularLines.length; i++) {
            const lineA = regularLines[i];
            if (merged.has(lineA.id)) {
                continue;
            }

            for (let j = i + 1; j < regularLines.length; j++) {
                const lineB = regularLines[j];
                if (merged.has(lineB.id)) {
                    continue;
                }

                if (
                    lineA.product_id?.id === lineB.product_id?.id &&
                    lineA.getDiscount() === lineB.getDiscount() &&
                    lineA.getDiscount() > 0 &&
                    lineA.price_unit === lineB.price_unit &&
                    lineA.full_product_name === lineB.full_product_name &&
                    !lineA.combo_parent_id &&
                    !lineB.combo_parent_id &&
                    !lineA.isLotTracked?.() &&
                    !lineB.isLotTracked?.() &&
                    !lineA.refunded_orderline_id &&
                    !lineB.refunded_orderline_id
                ) {
                    lineA.setQuantity(lineA.getQuantity() + lineB.getQuantity(), true);
                    merged.add(lineB.id);
                    lineB.delete();
                }
            }
        }
    },
});
