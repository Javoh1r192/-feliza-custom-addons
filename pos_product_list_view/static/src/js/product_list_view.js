/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { useState, reactive, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";

const STORAGE_KEY = "pos_product_view_mode";

// Do'kon (POS ombori) qoldig'i — jonli, keshga bog'liq emas: {tmpl_id: qty}
export const STORE_STOCK = reactive({ map: {}, loaded: false });

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.viewState = useState({ mode: localStorage.getItem(STORAGE_KEY) || "grid" });
        const orm = useService("orm");
        onWillStart(async () => {
            if (STORE_STOCK.loaded) {
                return;
            }
            try {
                const res = await orm.call("pos.config", "get_store_stock", [this.pos.config.id]);
                STORE_STOCK.map = res || {};
                STORE_STOCK.loaded = true;
            } catch (e) {
                console.error("[pos_product_list_view] get_store_stock failed:", e);
            }
        });
    },
    get isListView() {
        return this.viewState.mode === "list";
    },
    get productCardClass() {
        return this.isListView
            ? "flex-row-reverse justify-content-between"
            : "flex-column";
    },
    setViewMode(mode) {
        this.viewState.mode = mode;
        localStorage.setItem(STORAGE_KEY, mode);
    },
});

patch(ProductCard.prototype, {
    get priceStr() {
        const p = this.props.product;
        if (!p) {
            return "";
        }
        const v = Math.round(p.lst_price || p.list_price || p.price || 0);
        try {
            return v.toLocaleString("ru-RU");
        } catch (e) {
            return String(v);
        }
    },
    get storeQty() {
        const p = this.props.product;
        if (!p) {
            return 0;
        }
        const tid = (p.product_tmpl_id && p.product_tmpl_id.id) ? p.product_tmpl_id.id : p.id;
        const v = STORE_STOCK.map[tid];
        return v === undefined ? 0 : v;
    },
});
