import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";


patch(ProductScreen.prototype, {

    getNumpadButtons() {
        const buttons = super.getNumpadButtons();
        const employee = this.pos.cashier;
        for (const button of buttons) {
            if (button.value === "quantity") {
                button.disabled = button.disabled || employee.pw_disable_qty;
            }
            if (button.value === "price") {
                button.disabled = button.disabled || employee.pw_disable_price;
            }
            if (button.value === "discount") {
                button.disabled = button.disabled || employee.pw_disable_discount;
            }
            if (button.value === "-") {
                button.disabled = button.disabled || employee.pw_disable_pos_numpad_plus_minus;
            }
        }
        const clickButton = buttons.find(button => button.value === this.pos.numpadMode);
        if (clickButton) {
            for (const button of buttons) {
                if (!["quantity", "discount", "price", "-"].includes(button.value)) {
                    button.disabled = clickButton.disabled;
                }
            }
        }
        return buttons;
    },
})