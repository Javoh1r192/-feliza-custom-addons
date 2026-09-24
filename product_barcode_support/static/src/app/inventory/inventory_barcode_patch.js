/** @odoo-module */

import { MainComponent } from "@stock_barcode/components/main";
import { ProductSelectionPopup } from "@product_barcode_support/app/popups/product_selection_popup";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(MainComponent.prototype, {
    /**
     * Barcode moduli ichida har qanday skanerlash hodisasi shu metodga keladi
     * @override
     */
    async _onBarcodeScanned(barcode) {
        if (!barcode) {
            return super._onBarcodeScanned(barcode);
        }

        try {
            // 1. Bazadan shtrix-kod bo'yicha barcha variantlarni qidiramiz
            const products_data = await this.env.services.orm.search_read(
                "product.product",
                [["barcode", "=", barcode]],
                ["id", "display_name", "lst_price"]
            );

            // Agar 1 ta bo'lsa yoki topilmasa - standart Odoo mantiqi davom etadi
            if (!products_data || products_data.length <= 1) {
                return super._onBarcodeScanned(barcode);
            }

            // 2. Agar bir nechta kitob chiqsa, dialog xizmati orqali bizning popupni ochamiz
            const selectedProductId = await new Promise((resolve) => {
                this.env.services.dialog.add(ProductSelectionPopup, {
                    products: products_data,
                    title: _t("Shtrix-kod bir nechta kitobda aniqlandi"),
                    confirm: (id) => resolve(id),
                    cancel: () => resolve(null),
                });
            });

            if (selectedProductId) {
                // 3. Foydalanuvchi kerakli kitobni (masalan, Qattiq muqovaligini) tanladi.
                // Endi Barcode App chalkashib ketmasligi uchun unga shtrix-kod o'rniga,
                // tanlangan aniq mahsulotning ID raqamini "Virtual shtrix-kod" sifatida uzatamiz.
                // Odoo Barcode App default holatda mahsulot ID raqamini ham qabul qila oladi.

                return super._onBarcodeScanned(selectedProductId.toString());
            }

            return false;
        } catch (error) {
            console.error("Barcode App Multi-Product Error:", error);
            return super._onBarcodeScanned(barcode);
        }
    }
});