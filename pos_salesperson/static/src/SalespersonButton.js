/** @odoo-module **/
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { SalespersonPopup } from "./SalespersonPopup";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

export class SalespersonButton extends Component {
    static template = "pos_salesperson.SalespersonButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    get currentOrder() { return this.pos.getOrder(); }
    get salesperson() { return this.currentOrder?.salesperson_emp_id || null; }

    get employees() {
        try {
            const m = this.pos.models["hr.employee"];
            const all = m && m.getAll ? m.getAll() : m && m.records ? Object.values(m.records) : [];
            return all.filter(e => e._role === 'minimal');
        } catch (e) {}
        return [];
    }

    onClick() {
        this.dialog.add(SalespersonPopup, {
            title: "Sotuvchini tanlang",
            employees: this.employees,
            currentSalesperson: this.salesperson,
            onSelect: (emp) => { if (this.currentOrder) this.currentOrder.salesperson_emp_id = emp; },
        });
    }
}

ControlButtons.components = {
    ...ControlButtons.components,
    SalespersonButton,
};
