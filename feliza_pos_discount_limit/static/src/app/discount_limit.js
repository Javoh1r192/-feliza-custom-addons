/** @odoo-module */
/*
    Feliza POS Discount Limit — frontend cheklovi
    =============================================
    Kassirning maksimal chegirma limitidan oshiq chegirma KIRITILSA, uni
    limitgacha kamaytiradi va ogohlantirish ko'rsatadi. Barcha qo'lda
    kiritish yo'llari (numpad "%", barcode) store'ning setDiscountFromUI
    metodidan o'tgani uchun shu yagona nuqta ushlangan.

    MUHIM (2026-09-01 da qo'shildi):
    Aksiya dasturi (Skidki i loyalnost) bergan chegirma kassirning
    limitiga BOG'LIQ EMAS. Masalan 50% aksiyadagi tovarni 25% limitli
    kassir ham sotishi kerak. Shuning uchun chegirma foizi shu tovarga
    belgilangan aksiya foiziga teng bo'lsa — cheklov qo'llanmaydi.
*/
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

function felizaReadMax(record) {
    if (!record) {
        return null;
    }
    const v = record.pos_max_discount;
    return v === undefined || v === null ? null : v;
}

function felizaYumaloq(x) {
    return Math.round((parseFloat(x) || 0) * 100) / 100;
}

/**
 * Shu tovarga aksiya dasturi beradigan chegirma foizlari.
 * Qaytadi: Set (masalan {30, 50}).
 */
function felizaAksiyaFoizlari(line) {
    const foizlar = new Set();
    try {
        const models = line.models || line.order_id?.models;
        const mukofotlar =
            (models && models["loyalty.reward"] && models["loyalty.reward"].getAll())
            || [];
        const tovarId = line.product_id && line.product_id.id;
        for (const r of mukofotlar) {
            if (r.reward_type !== "discount" || r.discount_mode !== "percent") {
                continue;
            }
            if (r.discount_applicability !== "specific") {
                foizlar.add(felizaYumaloq(r.discount));
                continue;
            }
            const idlar = (r.all_discount_product_ids || []).map((p) =>
                typeof p === "number" ? p : p.id
            );
            if (idlar.includes(tovarId)) {
                foizlar.add(felizaYumaloq(r.discount));
            }
        }
    } catch {
        // aniqlab bo'lmasa — cheklov odatdagidek ishlaydi
    }
    return foizlar;
}

patch(PosStore.prototype, {
    // Joriy kassirning (yoki foydalanuvchining) maksimal chegirma foizi
    felizaGetMaxDiscount() {
        let max = null;
        try {
            max = felizaReadMax(this.getCashier && this.getCashier());
        } catch (e) {
            max = null;
        }
        if (max === null) {
            max = felizaReadMax(this.user);
        }
        return max === null ? 100 : max;
    },

    async setDiscountFromUI(line, val) {
        const max = this.felizaGetMaxDiscount();
        const numeric = parseFloat(val);
        if (!isNaN(numeric) && max < 100 && numeric > max) {
            // aksiya foizi bo'lsa — to'smaymiz
            if (!felizaAksiyaFoizlari(line).has(felizaYumaloq(numeric))) {
                this.notification.add(
                    _t("Siz eng ko'pi bilan %s%% chegirma bera olasiz.", max),
                    { type: "warning" }
                );
                val = max;
            }
        }
        return super.setDiscountFromUI(line, val);
    },
});

patch(PosOrderline.prototype, {
    // Xavfsizlik to'sig'i: qaysi yo'l bilan bo'lmasin, limitdan oshmaydi.
    // Aksiya chegirmasi bundan mustasno.
    setDiscount(discount) {
        let max = 100;
        try {
            const order = this.order_id;
            const cashier = order && (order.employee_id || order.user_id);
            const m = felizaReadMax(cashier);
            if (m !== null) {
                max = m;
            }
        } catch (e) {
            max = 100;
        }
        const numeric = parseFloat(discount);
        if (!isNaN(numeric) && max < 100 && numeric > max) {
            if (!felizaAksiyaFoizlari(this).has(felizaYumaloq(numeric))) {
                discount = max;
            }
        }
        return super.setDiscount(discount);
    },
});
