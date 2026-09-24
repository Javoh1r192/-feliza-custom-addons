/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Sotuvchi tanlash dialogi.
 *
 * Props:
 *   title            {String}       – dialog sarlavhasi
 *   employees        {Array}        – [{id, name}, ...]  – tanlash uchun ro'yxat
 *   currentSalesperson {Object|null} – hozirgi tanlangan sotuvchi yoki null
 *   onSelect         {Function}     – (employee) => void  – sotuvchi tanlanganda
 *   close            {Function}     – dialogni yopish (Odoo dialog service to'ldirishadi)
 */
export class SalespersonPopup extends Component {
    static template = "pos_salesperson.SalespersonPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        employees: Array,
        currentSalesperson: { optional: true },
        onSelect: Function,
        close: Function,
    };
    static defaultProps = {
        title: "Sotuvchini tanlang",
        currentSalesperson: null,
    };

    onSelect(emp) {
        this.props.onSelect(emp);
        this.props.close();
    }

    onRemove() {
        this.props.onSelect(null);
        this.props.close();
    }
}
