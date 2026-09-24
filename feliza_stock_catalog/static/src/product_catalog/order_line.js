import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/views/fields/formatters";
import { _t } from "@web/core/l10n/translation";

// ---------------------------------------------------------------------------
//  ОСТАТОК НА КАРТОЧКЕ КАТАЛОГА
//
//  Бэкенд (stock_picking.py -> _get_product_price_and_data) присылает
//  дополнительное поле `qtyAvailable`. Компонент проверяет props по схеме,
//  поэтому новое поле нужно объявить — иначе OWL выдаст ошибку props.
// ---------------------------------------------------------------------------
ProductCatalogOrderLine.props = {
    ...ProductCatalogOrderLine.props,
    qtyAvailable: { type: Number, optional: true },
    mainStocks: { type: Array, optional: true },
};

patch(ProductCatalogOrderLine.prototype, {
    /** Есть ли что показывать (на приёмках остаток может не приходить). */
    get hasStock() {
        return this.props.qtyAvailable !== undefined
            && this.props.qtyAvailable !== null;
    },

    /** «12» — целое число, без лишних нулей. */
    get stockLabel() {
        const n = Number(this.props.qtyAvailable) || 0;
        return formatFloat(n, { digits: [false, 0], thousandsSep: " " });
    },

    /**
     * Свой остаток — ВСЕГДА нейтральный.
     * На заявке ноль у себя — это норма (за тем и заявка), а на отгрузке
     * товары с нулём вообще отфильтрованы. То есть красный здесь красил бы
     * весь экран, ничего не сообщая. Красный оставлен только для второй
     * строки — там ноль действительно означает «заявку слать бесполезно».
     */
    get stockClass() {
        return "fsc-stock";
    },

    // ---- СПРАВОЧНЫЕ СКЛАДЫ ----
    // Магазины отсюда оформляют заявки, поэтому под своим остатком
    // показывается наличие там, откуда товар приедет. Складов может быть
    // несколько — по строке на каждый.

    get mainStocks() {
        return this.props.mainStocks || [];
    },

    /** «12» — целое число, без лишних нулей. */
    fmtQty(qty) {
        const n = Number(qty) || 0;
        return formatFloat(n, { digits: [false, 0], thousandsSep: " " });
    },

    /** Ноль на складе-источнике = заявку слать бессмысленно. */
    mainClass(qty) {
        return (Number(qty) || 0) <= 0 ? "fsc-main fsc-main-none" : "fsc-main";
    },
});

// ---------------------------------------------------------------------------
//  КНОПКА ВОЗВРАТА
//
//  Штатный каталог рассчитан на продажи и пишет «Назад к Коммерческим
//  предложениям» — на складском документе это сбивает с толку.
// ---------------------------------------------------------------------------
patch(ProductCatalogKanbanController.prototype, {
    _defineButtonContent() {
        const res = super._defineButtonContent(...arguments);
        // orderResModel заполняется из context.product_catalog_order_model
        if (this.orderResModel === "stock.picking") {
            this.buttonString = _t("Back to Transfer");
        }
        return res;
    },
});
