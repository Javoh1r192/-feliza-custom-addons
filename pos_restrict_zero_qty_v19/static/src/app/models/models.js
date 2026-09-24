/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {

    /**
     * To'lovga o'tishdan oldin ombor qoldig'ini tekshiradi.
     *
     * Avvalgi versiyaga nisbatan ikkita farq:
     *
     *  1. Savatdagi hamma tovar BITTA so'rovda tekshiriladi. Avval har bir
     *     qatorga alohida so'rov ketardi — 5 tovarli savatda 5 marta.
     *
     *  2. Server bilan aloqa uzilsa savdo TO'XTAMAYDI. Avval so'rov xato
     *     bergani uchun `super.pay()` umuman chaqirilmasdi va kassir to'lov
     *     oynasiga o'ta olmasdi. Endi sessiya boshida kassaga yuklangan
     *     `qty_available` ishlatiladi va kassirga ogohlantirish ko'rsatiladi.
     *
     *     Yuklangan qoldiq — barcha omborlar bo'yicha JAMI, ya'ni do'kon
     *     qoldig'idan kichik bo'la olmaydi. Shuning uchun undan ham oshib
     *     ketgan holatnigina to'samiz: noto'g'ri taqiqlash bo'lmaydi.
     */
    async pay() {
        const pos = this.env.services.pos;

        if (!pos.config.restrict_zero_qty) {
            return super.pay(...arguments);
        }

        const order = pos.getOrder();
        const lines = order ? order.getOrderlines() : [];

        // Savatni yig'amiz: bitta tovar bir necha qatorda bo'lsa, qo'shiladi
        const needed = new Map();
        for (const line of lines) {
            const prd = line.product_id;
            if (!prd || prd.type === "service" || !(line.qty > 0)) {
                continue;
            }
            const entry = needed.get(prd.id);
            if (entry) {
                entry.qty += line.qty;
            } else {
                needed.set(prd.id, { product: prd, qty: line.qty });
            }
        }

        if (needed.size === 0) {
            return super.pay(...arguments);
        }

        // Bitta so'rov — hamma tovar uchun
        let stockInfo = null;
        let offline = false;
        try {
            stockInfo = await this.env.services.orm.call(
                "product.product",
                "get_products_stock_info",
                [[...needed.keys()]],
                { config_id: this.config.id }
            );
        } catch {
            offline = true;
        }

        for (const [productId, item] of needed) {
            let available;
            let whName;

            if (!offline) {
                const info = stockInfo && stockInfo[productId];
                if (!info || info.error) {
                    // Ma'lumot yo'q — avvalgi xatti-harakat: to'smaymiz
                    continue;
                }
                available = info.qty;
                whName = info.warehouse_name;
            } else {
                const local = item.product.qty_available;
                if (local === undefined || local === null) {
                    continue;
                }
                available = local;
                whName = _t("aloqa yo'q — taxminiy qoldiq");
            }

            if (available < item.qty) {
                const product = this.models["product.product"].getBy("id", parseInt(productId));
                this.dialog.add(AlertDialog, {
                    title: _t('🛑 Sotuv taqiqlandi'),
                    body: _t(
                        `Mahsulot: ${(product || item.product).display_name}\n\n` +
                        `📍 Ombor: ${whName}\n` +
                        `📦 Ombor qoldig'i: ${available} ta\n` +
                        `🛒 Kerakli miqdor: ${item.qty} ta\n\n` +
                        `Ombor qoldig'i yetarli emas!`
                    ),
                });
                return;
            }
        }

        if (offline) {
            this.env.services.notification?.add(
                _t("Server bilan aloqa yo'q. Ombor qoldig'i tekshirilmadi — savdo oflayn davom etmoqda."),
                { type: "warning" }
            );
        }

        await super.pay(...arguments);
    },
});
