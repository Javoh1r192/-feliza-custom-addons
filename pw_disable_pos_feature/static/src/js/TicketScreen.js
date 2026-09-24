/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async addProductToOrder(product) {
        const cashier = this.pos.cashier;
        localStorage.setItem(
            "pw_disable_remove_orderline",
            JSON.stringify(cashier.pw_disable_remove_orderline)
        );
        if (cashier.pw_disable_products === true&& product.name !== 'Chegirma') {
            this.notification.add("Mahsulot qo‘shish bloklangan!", {
                type: "danger",
            });
            return;
        }
        return super.addProductToOrder(...arguments);
    },

    getNumpadButtons() {
        const result = super.getNumpadButtons(...arguments);
        const cashier = this.pos.cashier;
        localStorage.setItem(
            "pw_disable_remove_orderline",
            JSON.stringify(cashier.pw_disable_remove_orderline)
        );
        result.forEach((button) => {
            if (button.value === "quantity" && cashier.pw_disable_qty) {
                button.disabled = true;
                button.class = "pw_disable_button";
            }
            if (button.value === "discount" && cashier.pw_disable_discount) {
                button.disabled = true;
                button.class = "pw_disable_button";
            }
            if (button.value === "price" && cashier.pw_disable_price) {
                button.disabled = true;
                button.class = "pw_disable_button";
            }
            if (button.value === "Backspace" && cashier.pw_disable_remove_orderline) {
                button.disabled = true;
                button.class = "pw_disable_button";
            }
        });

        return result;
    },
});
