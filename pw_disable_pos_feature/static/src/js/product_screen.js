/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {

    async addProductToOrder(product) {
        const cashier = this.pos.cashier;
        localStorage.setItem(
            "pw_disable_remove_orderline",
            JSON.stringify(cashier.pw_disable_remove_orderline)
        );
        if (cashier.pw_disable_products === true && product.name !== 'Chegirma') {
            this.notification.add("Mahsulot qo‘shish bloklangan!", {
                type: "danger",
            });
            return;
        }
        return super.addProductToOrder(...arguments);
    },

    setup() {
        super.setup(...arguments);
        const cashier = this.pos.cashier;

        localStorage.setItem(
            "pw_disable_remove_orderline",
            JSON.stringify(cashier.pw_disable_remove_orderline)
        );

    },


    getNumpadButtons() {
        const result = super.getNumpadButtons(...arguments);
        const cashier = this.pos.cashier;



        result.forEach((button) => {
            if (button.value === 'quantity' && cashier.pw_disable_qty === true) {
                button.disabled = true;
                button.class = 'pw_disable_button';
            }
            if (button.value === 'discount' && cashier.pw_disable_discount === true) {
                button.disabled = true;
                button.class = 'pw_disable_button';
            }
            if (button.value === 'price' && cashier.pw_disable_price === true) {
                button.disabled = true;
                button.class = 'pw_disable_button';
            }
            if (button.value === 'Backspace' && cashier.pw_disable_remove_orderline === true) {
                button.disabled = true;
                button.class = 'pw_disable_button';
            }
        });
        return result;
    },
});
