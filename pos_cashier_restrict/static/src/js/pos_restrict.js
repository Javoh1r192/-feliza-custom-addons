/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

/**
 * Patch ProductScreen.getNumpadButtons() so that discount (%) and price
 * buttons are hidden per-cashier based on hr.employee boolean flags:
 *   pw_disable_discount  →  hides the "%" button
 *   pw_disable_price     →  hides the "Price" button
 *
 * Odoo 19 compatible version:
 *  - getCashier() usulini xavfsiz chaqiradi
 *  - this.pos mavjudligini tekshiradi
 *  - super() to'g'ri argument bilan chaqiriladi
 */
patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons();

        // pos yuklanmagan bo'lsa — standart buttonlarni qaytaramiz
        if (!this.pos) {
            return buttons;
        }

        let cashier = null;
        try {
            cashier = this.pos.getCashier?.() ?? this.pos.cashier ?? null;
        } catch (e) {
            // getCashier xato bersa — chiqib ketmaymiz
            return buttons;
        }

        if (!cashier) {
            return buttons;
        }

        return buttons.map((button) => {
            if (button.value === "discount" && cashier.pw_disable_discount) {
                return {
                    ...button,
                    class: ((button.class || "") + " invisible").trim(),
                    disabled: true,
                };
            }
            if (button.value === "price" && cashier.pw_disable_price) {
                return {
                    ...button,
                    class: ((button.class || "") + " invisible").trim(),
                    disabled: true,
                };
            }
            return button;
        });
    },
});
