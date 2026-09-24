/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { getWalletBalance, getWalletCard, getWalletProgram } from "../../utils/wallet_utils";

/**
 * To'lov ekranida mijozning joriy cashback balansi (va shu buyurtmada
 * allaqachon qancha ishlatilayotgani) doim ko'rinib turishi kerak.
 * Balans — mijozning Odoo Loyalty kartasidan (native) o'qiladi.
 *
 * Bu balans namoyishi sof UX qatlami — haqiqiy balans va uning o'zgarishi
 * har doim serverda hisoblanadi (res_partner.py -> _wallet_spend YAKUNIY
 * himoya nuqtasi), bu yerda faqat kassirga ma'lumot ko'rsatiladi.
 *
 * MUHIM: POS frontendidagi `loyalty.card.points` mahalliy keshi — native
 * Odoo'ning o'zi TO'PLASH (earn) bo'yicha buyurtma javobi orqali avtomatik
 * yangilaydi, lekin bizning modulimizdagi SARFLASH (spend) uchun bunday
 * avtomatik "push" mexanizmi yo'q. Natijada, agar kassir bir nechta
 * buyurtmani ORQAGA (Odoo backend ilovalar ro'yxatiga) qaytmasdan, faqat
 * ichki "New Order" tugmasi orqali ketma-ket bajarsa, ekrandagi balans
 * ESKIRGAN (haqiqatdan OSHIRILGAN) bo'lib qolishi mumkin — jonli sinovda
 * aniq tasdiqlangan xato. Shuning uchun to'lov ekrani ochilganda (va
 * mijoz tanlanganda) mijozning cashback kartasi ballarini serverdan
 * DARHOL qayta o'qib, mahalliy keshni yangilaymiz — bu ekrandagi
 * ko'rsatkichni deyarli har doim to'g'ri qiladi va shu bilan birga
 * server tomonidagi qattiq tekshiruvda keraksiz bloklanishlarni
 * kamaytiradi (garchi YAKUNIY himoya baribir serverda qoladi).
 */
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._refreshWalletBalanceFromServer();
    },

    async _refreshWalletBalanceFromServer() {
        const order = this.currentOrder;
        const partner = order && order.partner_id;
        if (!partner) {
            return;
        }
        try {
            let card = getWalletCard(this.pos.models, partner);
            if (!card) {
                // MUHIM TUZATISH (2026-09-02): POS ochilganda faqat bir
                // qism mijozlar (va ularning kartalari) oldindan yuklanadi.
                // Qidiruv orqali topilgan mijozning kartasi mahalliy
                // xotirada BO'LMASLIGI mumkin — avvalgi kod bu holatda jim
                // qaytar va balans 0 bo'lib ko'rinar edi ("cashback bir
                // chiqib bir chiqmaydi" muammosining sababi). Endi karta
                // topilmasa, serverdan qidirib olamiz — searchRead natijani
                // mahalliy modelga o'zi qo'shadi, keyin banner va summa
                // cheklovi to'g'ri ishlaydi.
                const program = getWalletProgram(this.pos.models);
                if (!program) {
                    return;
                }
                await this.pos.data.searchRead(
                    "loyalty.card",
                    [
                        ["partner_id", "=", partner.id],
                        ["program_id", "=", program.id],
                    ],
                    this.pos.data.fields["loyalty.card"],
                    { limit: 1 }
                );
                card = getWalletCard(this.pos.models, partner);
                if (!card) {
                    return;      // mijozda haqiqatan karta yo'q — balans 0
                }
            } else {
                await this.pos.data.read("loyalty.card", [card.id], ["points"]);
            }
        } catch {
            // Tarmoq yo'q yoki xato bo'lsa jim o'tkazib yuboramiz — bu
            // faqat qulaylik uchun, yakuniy tekshiruv baribir serverda.
        }
    },

    getWalletBalanceInfo() {
        const order = this.currentOrder;
        const partner = order && order.partner_id;
        if (!partner) {
            return null;
        }
        const balance = getWalletBalance(this.pos.models, partner);
        const usedOnOrder = ((order && order.payment_ids) || [])
            .filter(
                (line) => line.payment_method_id && line.payment_method_id.is_wallet_payment
            )
            .reduce((sum, line) => sum + (line.amount || 0), 0);

        return {
            balance,
            used: usedOnOrder,
            remaining: Math.max(balance - usedOnOrder, 0),
        };
    },

    formatWalletAmount(value) {
        // Odoo'ning ichki valyuta formatlash yordamchisiga bog'liq bo'lmaslik
        // uchun (versiyalar orasida nomi o'zgarishi mumkin), oddiy son
        // formatlashdan foydalanamiz.
        try {
            return Number(value || 0).toLocaleString("uz-UZ", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2,
            });
        } catch {
            return String(value);
        }
    },
});
