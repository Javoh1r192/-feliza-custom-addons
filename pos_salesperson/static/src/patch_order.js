/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.salesperson_emp_id = this.salesperson_emp_id ? this.salesperson_emp_id.id : null;
        return json;
    },
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.salesperson_emp_id = this.salesperson_emp_id || null;
        return result;
    },
});
