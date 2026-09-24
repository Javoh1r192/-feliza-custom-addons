/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    async searchPartner() {
        // MUHIM: native natijani saqlab qolish va oxirida qaytarish shart -
        // Odoo o'zining onEnter() metodida shu natijani (masalan
        // result.length) ishlatadi. Agar bu yerda hech narsa qaytarilmasa,
        // onEnter() "undefined.length" o'qishga urinib, "Cannot read
        // properties of undefined (reading 'length')" xatosini beradi.
        const result = await super.searchPartner(...arguments);

        const query = (this.state.query || "").trim();
        if (query.length < 7) {
            return result;
        }
        const digits = query.replace(/[^0-9]/g, "");
        if (digits.length < 7) {
            return result;
        }
        const all = [
            ...(this.state.initialPartners || []),
            ...(this.state.loadedPartners || []),
        ];
        const filtered = typeof this.getPartners === "function"
            ? this.getPartners(all)
            : all;
        if (filtered.length === 1) {
            this.clickPartner(filtered[0]);
        }
        return result;
    },
});
