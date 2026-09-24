/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
    },

    getDisplayData() {
        let disableProducts = false;
        const saved = localStorage.getItem("pw_disable_remove_orderline");
        if (saved == 'true') {
            disableProducts = true;
        }
        return {
            ...super.getDisplayData(),
            pw_disable_remove_orderline: disableProducts,
        };
    },
});

// Orderline props ni xavfsiz kengaytirish
try {
    const lineProps = Orderline.props && Orderline.props.line;
    const lineShape = lineProps && lineProps.shape;
    if (lineShape) {
        patch(Orderline, {
            props: {
                ...Orderline.props,
                line: {
                    ...lineProps,
                    shape: {
                        ...lineShape,
                        pw_disable_remove_orderline: { type: Boolean, optional: true },
                    },
                },
            },
        });
    }
} catch (e) {
    console.warn("[pw_disable] Orderline props patch o'tkazib yuborildi:", e.message);
}
