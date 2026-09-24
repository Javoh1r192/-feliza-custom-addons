import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";

/**
 * Gift card (vaucher) reward qatori uchun kassir kiritgan summani saqlash va
 * Odoo'ning reward qayta hisoblashida hurmat qilish.
 *
 * uiState.giftCardManualAmounts = { [coupon_id]: amount (musbat, so'mda) }
 * uiState IndexedDB'ga saqlanadi, shuning uchun sahifa yangilansa ham qoladi.
 */
patch(PosOrder.prototype, {
    initState() {
        super.initState(...arguments);
        this.uiState.giftCardManualAmounts = this.uiState.giftCardManualAmounts || {};
    },
    restoreState(vals) {
        super.restoreState(...arguments);
        this.uiState.giftCardManualAmounts = this.uiState.giftCardManualAmounts || {};
    },

    /** Kassir kiritgan summa (yoki undefined). */
    getGiftCardManualAmount(couponId) {
        const amounts = this.uiState.giftCardManualAmounts || {};
        const val = amounts[couponId];
        return typeof val === "number" && val > 0 ? val : undefined;
    },
    setGiftCardManualAmount(couponId, amount) {
        if (!this.uiState.giftCardManualAmounts) {
            this.uiState.giftCardManualAmounts = {};
        }
        if (amount === undefined || amount === null) {
            delete this.uiState.giftCardManualAmounts[couponId];
        } else {
            this.uiState.giftCardManualAmounts[couponId] = amount;
        }
    },

    /**
     * Berilgan gift card uchun bu orderda ishlatilishi mumkin bo'lgan maksimal
     * summa: kartaning to'liq balansi (shu orderdagi mavjud reward qatori
     * hisobga olinmagan holda) va order'ning chegirma qilinadigan summasi.
     */
    getGiftCardMaxUsable(couponId, reward) {
        let points = this._getRealCouponPoints(couponId);
        for (const line of this.getOrderlines()) {
            if (line.is_reward_line && line.coupon_id?.id === couponId) {
                points += line.points_cost;
            }
        }
        const balance = points * (reward?.discount || 1);
        const { discountable } = this._getDiscountableOnOrder(reward);
        return {
            balance,
            discountable: Math.min(this.priceIncl, discountable),
            max: Math.min(balance, Math.min(this.priceIncl, discountable)),
        };
    },

    /**
     * Gift card uchun: agar kassir summa kiritgan bo'lsa, standart hisoblangan
     * qatorni shu summagacha cheklaymiz.
     */
    _getRewardLineValuesDiscount(args) {
        const result = super._getRewardLineValuesDiscount(...arguments);
        const reward = args["reward"];
        const couponId = args["coupon_id"];
        if (
            !Array.isArray(result) ||
            !result.length ||
            reward.program_id.program_type !== "gift_card"
        ) {
            return result;
        }
        const manual = this.getGiftCardManualAmount(couponId);
        if (manual === undefined) {
            return result;
        }
        const line = result[0];
        const autoAmount = -line.price_unit; // standart: min(balans, order)
        if (manual >= autoAmount) {
            return result; // kassir kiritgan summa baribir yetmaydi - standart qoladi
        }
        // Standart bilan bir xil usulda, lekin cheklangan summa bilan qayta hisoblaymiz
        const discountProduct = reward.discount_line_product_id;
        const baseLine = discountProduct.getBaseLine({
            overridedValues: {
                tax_ids: discountProduct.taxes_id,
                price_unit: -manual,
                quantity: 1,
                special_mode: "total_included",
            },
        });
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, this.company);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], this.company);
        accountTaxHelpers.fix_base_lines_tax_details_on_manual_tax_amounts(
            [baseLine],
            this.company
        );
        const extraTaxData = accountTaxHelpers.export_base_line_extra_tax_data(baseLine);
        return [
            {
                ...line,
                price_unit: baseLine.price_unit,
                points_cost: manual / (reward.discount || 1),
                extra_tax_data: extraTaxData,
            },
        ];
    },

    /**
     * Kassir summani cheklaganidan keyin kartada hali ball qoladi va Odoo
     * uni "yana claim qilsa bo'ladi" deb qayta-qayta yangi Gift Card qatorlari
     * qo'shaveradi. Qo'lda summa kiritilgan karta uchun bu orderda allaqachon
     * qator bo'lsa - qayta claim qilinmaydi.
     */
    getClaimableRewards(coupon_id, program_id, auto) {
        const result = super.getClaimableRewards(...arguments);
        if (!Array.isArray(result)) {
            return result;
        }
        return result.filter((claim) => {
            if (claim.reward?.program_id?.program_type !== "gift_card") {
                return true;
            }
            if (this.getGiftCardManualAmount(claim.coupon_id) === undefined) {
                return true;
            }
            const alreadyApplied = this.lines.some(
                (l) => l.is_reward_line && l.coupon_id?.id === claim.coupon_id
            );
            return !alreadyApplied;
        });
    },

    /**
     * Reward qatorlari qayta yaratilganda tanlangan qator o'chib ketadi va
     * kassir numpad'da yozayotgan raqamlar "havoga" ketadi. Shu coupon'ning
     * yangi qatorini qayta tanlab qo'yamiz.
     */
    _updateRewardLines() {
        const selected = this.getSelectedOrderline();
        const couponId =
            selected && selected.is_reward_line && selected.coupon_id
                ? selected.coupon_id.id
                : null;
        const res = super._updateRewardLines(...arguments);
        if (couponId && !this.getSelectedOrderline()) {
            const line = this.lines.find(
                (l) => l.is_reward_line && l.coupon_id?.id === couponId
            );
            if (line) {
                this.selectOrderline(line);
            }
        }
        return res;
    },
});
