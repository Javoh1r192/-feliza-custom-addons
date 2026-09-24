/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.payment_methods_from_config = this.pos.config.payment_method_ids
            .slice()
            .sort((a, b) => a.sequence - b.sequence);
        const cashier = this.pos.cashier;   
        if (cashier && cashier.pw_disable_customer_account === true) {
            this.payment_methods_from_config = this.payment_methods_from_config.filter(
                (pm) => pm.type !== "pay_later"   
            );
        }
    },
});
