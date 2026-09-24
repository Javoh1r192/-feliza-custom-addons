/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductSelectionPopup } from "../popups/product_selection_popup";
import { _t } from "@web/core/l10n/translation";

// Odoo 19 dagi barcha skanerlashni boshqaradigan asosiy xizmat ob'ektini yuklaymian
import { barcodeService } from "@web/core/barcode/barcode_service";

console.log(">>> Multi Barcode: Web Barcode Service yuklanmoqda...");

patch(barcodeService, {
    /**
     * Odoo 19 da skaner tugmasi bosilganda ENGl birinchi ishlaydigan metod
     * @override
     */
    async trigger(barcode) {
        console.log(">>> Web Barcode Service: Kod skanerlandi:", barcode);

        if (!barcode) {
            return super.trigger(...arguments);
        }

        // Hozir POS (Kassa) muhitida ekanligimizni tekshiramiz
        // Chunki bu xizmat global hisoblanadi
        const posStore = odoo.__WOWL_DEBUG__?.root?.env?.services?.pos?.pos_store;
        const productMap = posStore?.env?.services?.pos_data?.records["product.product"];

        if (productMap) {
            const matched_products = [];
            for (const [id, product] of productMap.entries()) {
                if (product.barcode === barcode) {
                    matched_products.push(product);
                }
            }

            // Agar bitta shtrix-kod ostida birdan ortiq variant bo'lsa
            if (matched_products.length > 1) {
                console.log(">>> Web Barcode Service: Variantlar ko'p! Standart mantiq to'xtatildi.");

                // Biz yaratgan Popup oynani ochamiz
                posStore.env.services.dialog.add(ProductSelectionPopup, {
                    products: matched_products,
                    title: _t("Shtrix-kod bir nechta kitobda aniqlandi"),
                    confirm: (selectedProductId) => {
                        const selectedProduct = productMap.get(selectedProductId);
                        if (selectedProduct) {
                            // Tanlangan kitobni savatga qo'shish
                            posStore.addLineToCurrentOrder({
                                product_id: selectedProduct,
                                qty: 1,
                            });
                        }
                    },
                    close: () => {}
                });

                return; // Odoo kassa tizimiga signal umuman o'tib ketmasligi uchun SHU YERDA jarayonni uzamiz!
            }
        }

        // Agar muammo bo'lmasa, Odoo o'z ishlashini davom ettiradi
        return super.trigger(...arguments);
    }
});