/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

/**
 * MUHIM: native pos_loyalty moduli "bu buyurtma qancha ball beradi"
 * hisob-kitobini (order.uiState.couponPointChanges) faqat SAVATCHA
 * (mahsulot qatorlari, miqdor, mukofotlar) o'zgarganda avtomatik qayta
 * ishga tushiradi — TO'LOV qatorlari (masalan, kassir "Cashback"
 * to'lovini qo'shishi yoki summasini o'zgartirishi) o'zgarganda EMAS.
 *
 * Bizning pos_order.js override'imiz (pointsForPrograms) esa aynan
 * to'lov qatorlaridagi Cashback summasiga qarab ball hisob-kitobini
 * pasaytiradi. Agar bu hisob-kitob "Validate" bosilgan paytda qayta
 * ishga tushirilmasa, u ESKI (Cashback to'lov qatori hali to'liq
 * kiritilmagan yoki umuman qo'shilmagan paytdagi) qiymatda qolib ketishi
 * mumkin — natijada ball baribir noto'g'ri (oshirilgan) miqdorda
 * beriladi.
 *
 * Shuning uchun "Validate" bosilishi bilan, YAKUNIY to'lov holatiga
 * asoslanib, ball hisob-kitobini SERVERGA YUBORISHDAN OLDIN majburiy
 * yangilaymiz. Bu — native pos_loyalty'ning o'zi ham har bir savatcha
 * o'zgarishida ishlatadigan xuddi shu funksiya (orderUpdateLoyaltyPrograms),
 * shunchaki qo'shimcha bir marta, to'lov yakunlangandan keyin chaqirilmoqda.
 */
patch(OrderPaymentValidation.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos && this.pos.orderUpdateLoyaltyPrograms) {
            await this.pos.orderUpdateLoyaltyPrograms();
        }
        return super.validateOrder(...arguments);
    },
});
