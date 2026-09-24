/** @odoo-module */

import { Component } from "@odoo/owl";

export class ProductSelectionPopup extends Component {
    static template = "product_barcode_support.ProductSelectionPopup";
    static props = ["products", "title", "close", "confirm", "cancel"];

    selectProduct(productId) {
        if (this.props.confirm) {
            this.props.confirm(productId);
        }
        this.props.close();
    }

    cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.props.close();
    }
}