/** @odoo-module **/
/*
 * «Заказы» oynasidagi qidiruvga ARTIKUL va SHTRIX-KOD bandini qo'shadi.
 *
 * Odoo qidiruv bandlarini bitta joyda — _getSearchFields() da e'lon
 * qiladi. Har band uchta narsani beradi:
 *   repr        — ochiq cheklarni BRAUZERDA filtrlash uchun matn
 *   displayName — ro'yxatda ko'rinadigan nom
 *   modelFields — tasdiqlangan cheklarni SERVERDA qidirish uchun yo'l
 *
 * modelFields dagi bir nechta yo'l Odoo tomonidan «yoki» (OR) bilan
 * bog'lanadi — shuning uchun bitta band ham artikul, ham shtrix-kod
 * bo'yicha topadi. Kassir nima yozganini (yoki skanerlaganini)
 * o'ylab o'tirmaydi.
 */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

/* Chekdagi qatorlardan artikul va shtrix-kodlarni yig'ib beradi. */
function tovarKodlari(order) {
    const kodlar = [];
    for (const line of order.lines || []) {
        const tovar = line.product_id;
        if (!tovar) {
            continue;
        }
        if (tovar.default_code) {
            kodlar.push(String(tovar.default_code));
        }
        if (tovar.barcode) {
            kodlar.push(String(tovar.barcode));
        }
    }
    return kodlar;
}

patch(TicketScreen.prototype, {
    _getSearchFields() {
        const fields = super._getSearchFields(...arguments);
        fields.FELIZA_ARTIKUL = {
            repr: (order) => tovarKodlari(order).join(" "),
            displayName: _t("Artikul / Barcode"),
            // pos.order -> lines (pos.order.line) -> product_id -> ...
            // Ikkalasi Odoo tomonidan «|» (yoki) bilan bog'lanadi.
            modelFields: [
                "lines.product_id.default_code",
                "lines.product_id.barcode",
            ],
        };
        return fields;
    },

    /*
     * Odoo ochiq (hali serverga yuborilmagan) cheklarni fuzzyLookup bilan
     * filtrlaydi — u harflar KETMA-KET kelishini emas, faqat TARTIBDA
     * kelishini talab qiladi. Ya'ni «108044» so'rovi «107984 108021 …»
     * matniga ham tushib qoladi va noto'g'ri chek chiqadi.
     *
     * Server tomoni esa `ilike %108044%` — aniq bo'lak bo'yicha qidiradi.
     * Ikkalasi bir xil natija berishi uchun ochiq cheklarni qo'shimcha
     * ravishda ANIQ bo'lak bo'yicha suzamiz. fuzzy natijasi aniq
     * natijaning ustki to'plami bo'lgani uchun hech qanday to'g'ri chek
     * yo'qolmaydi — faqat yolg'on mosliklar olib tashlanadi.
     */
    getFilteredOrderList() {
        const orders = super.getFilteredOrderList(...arguments);
        const qidiruv = this.state.search;
        if (qidiruv.fieldName !== "FELIZA_ARTIKUL" || !qidiruv.searchTerm) {
            return orders;
        }
        const term = qidiruv.searchTerm.trim().toLowerCase();
        if (!term) {
            return orders;
        }
        return orders.filter((order) =>
            tovarKodlari(order).some((kod) => kod.toLowerCase().includes(term))
        );
    },
});
