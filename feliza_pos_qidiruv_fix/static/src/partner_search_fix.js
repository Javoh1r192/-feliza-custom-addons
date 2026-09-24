/** @odoo-module **/
/*
 * MUAMMO (Odoo 19 core, partner_list.js):
 *   getNewPartners() so'rov matni bo'yicha offsetni `offsetBySearch` da
 *   saqlaydi va uni hech qachon qayta boshlamaydi. Bir marta topilgan
 *   so'rov ikkinchi marta qidirilsa, server o'sha offsetdan qidiradi va
 *   yagona mos yozuvni o'tkazib yuboradi ("No more customer found").
 *   Bo'sh natija esa offsetga +100 qo'shadi — so'rov butunlay "zaharlanadi".
 *
 * TUZATMA: Enter bosilganda joriy so'rov uchun offset 0 ga qaytariladi.
 *   Takror kelgan yozuvlar baribir ikki marta qo'shilmaydi —
 *   loadedPartnerIds to'plami buni o'zi nazorat qiladi.
 */
import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    async onEnter() {
        // native onEnter ham DOM dan o'qiydi, lekin offsetni tozalash
        // uchun so'rov matni bizga SHU YERDA kerak
        const query = this.searchInputRef?.el
            ? this.searchInputRef.el.value
            : this.state.query;
        if (query && this.globalState?.offsetBySearch) {
            this.globalState.offsetBySearch[query] = 0;
        }
        return super.onEnter(...arguments);
    },
});
