/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { getWalletProgram } from "../utils/wallet_utils";

/**
 * MUAMMO: Cashback TO'PLASH (earn) hisob-kitobi native Odoo Loyalty
 * mexanizmi orqali butun buyurtma summasidan hisoblanadi — mijoz shu
 * buyurtmaning bir qismini AYNAN O'ZINING Cashback balansidan to'lagan
 * bo'lsa ham. Masalan: 100,000 so'mlik buyurtma, mijoz 20,000 so'mini
 * Cashback orqali to'laydi (qolgan 80,000 so'mni naqd/karta bilan) — eski
 * hisob-kitobda baribir 100,000 so'mning 1% i (1000 ball) beriladi, holbuki
 * mijoz haqiqatda faqat 80,000 so'm "yangi pul" kiritgan. Bu — mijoz o'z
 * ballaridan foydalanib, ustiga yana o'sha ballarning foizidan qayta ball
 * "ishlab olishi" (ball spiral effekti) va do'konning zarar ko'rishiga
 * olib keladi.
 *
 * YECHIM: native ball hisoblash FORMULASINING O'ZI (qoida, foiz, "necha
 * ball") umuman o'zgartirilmaydi — bu hali ham 100% Odoo Loyalty orqali
 * ishlaydi. Biz faqat BIZNING cashback hamyon dasturi uchun yakuniy
 * natijani, ushbu buyurtmada mijoz aynan shu hamyondan qancha TO'LAGANIGA
 * mos ravishda pasaytiramiz: agar buyurtmaning X% i Cashback bilan
 * to'langan bo'lsa, native hisoblangan ball ham xuddi shuncha % ga
 * kamaytiriladi. Boshqa barcha Loyalty/sodiqlik dasturlariga (agar
 * ularingiz bo'lsa) bu umuman tegmaydi.
 *
 * MUHIM (qachon to'g'ri ishlashi): bu hisob-kitob to'lov qatorlari
 * o'zgarganda avtomatik qayta ishga tushishi kerak — buning uchun
 * order_payment_validation.js override'iga qarang: u "Validate" bosilishi
 * bilan, YAKUNIY to'lov holatiga asoslanib, shu hisob-kitobni majburiy
 * qayta ishga tushiradi (native pos_loyalty buni faqat savat/mahsulot
 * qatorlari o'zgarganda avtomatik qiladi, to'lov qatorlari o'zgarganda
 * emas).
 */
patch(PosOrder.prototype, {
    pointsForPrograms(programs) {
        const result = super.pointsForPrograms(...arguments);

        const walletProgram = getWalletProgram(this.models);
        if (!walletProgram || !result[walletProgram.id] || !result[walletProgram.id].length) {
            return result;
        }

        const ratio = this._wallet_nonWalletPaidRatio();
        if (ratio >= 1) {
            // Bu buyurtmada Cashback bilan hech narsa to'lanmagan —
            // hisob-kitobni o'zgartirishning hojati yo'q.
            return result;
        }

        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        const round = (v) => (ProductPrice ? ProductPrice.round(v) : v);

        result[walletProgram.id] = result[walletProgram.id].map((entry) => ({
            ...entry,
            points: round((entry.points || 0) * ratio),
        }));

        return result;
    },

    /**
     * Ushbu buyurtma umumiy summasidan (soliq bilan) mijozning O'Z
     * Cashback balansi orqali QOPLANMAGAN — ya'ni boshqa to'lov turlari
     * orqali haqiqatda "yangi pul" sifatida kiritilgan — ulushini
     * qaytaradi (0 bilan 1 oralig'ida).
     *
     * Masalan: umumiy summa 100,000, Cashback orqali 20,000 to'langan —
     * natija 0.8 (ya'ni ball hisob-kitobi 80,000 so'm asosida bo'ladi).
     */
    _wallet_nonWalletPaidRatio() {
        const total = this.totalDue;
        if (!total || total <= 0) {
            return 1;
        }

        const walletPaid = (this.payment_ids || [])
            .filter((p) => p.payment_method_id && p.payment_method_id.is_wallet_payment)
            .reduce((sum, p) => sum + (p.amount || 0), 0);

        if (!walletPaid) {
            return 1;
        }

        return Math.max(0, Math.min(1, (total - walletPaid) / total));
    },
});
