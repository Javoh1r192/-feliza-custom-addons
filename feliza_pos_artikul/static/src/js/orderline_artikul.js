import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    /**
     * Savat satrida nomdan keyin ko'rsatiladigan artikul.
     * Bosma chekda ("receipt" rejimi) ko'rsatilmaydi.
     */
    get felizaArtikul() {
        if (this.props.mode === "receipt") {
            return false;
        }
        return this.line?.product_id?.default_code || false;
    },
});
