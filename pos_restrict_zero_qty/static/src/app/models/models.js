/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {

    async pay() {
        let order = this.env.services.pos.getOrder();
        let lines = order.getOrderlines();
        let prod_used_qty = {}; 

        if (this.env.services.pos.config.restrict_zero_qty) {
            for (let line of lines) {
                let prd = line.product_id;
                if (prd.type === 'service') {
                    continue;
                }
                
                const stock_info = await this.env.services.orm.call(
                    'product.product',
                    'get_product_stock_info',
                    [prd.id]
                );

                if (stock_info.error) continue;

                let available = stock_info.qty;
                let wh_name = stock_info.warehouse_name;

                if (prd.id in prod_used_qty) {
                    prod_used_qty[prd.id][1] += line.qty;
                } else {
                    prod_used_qty[prd.id] = [available, line.qty, wh_name];
                }
            }

            for (let [i, data] of Object.entries(prod_used_qty)) {
                let available = data[0];
                let needed = data[1];
                let wh_name = data[2];
                let product = this.models['product.product'].getBy('id', parseInt(i));
                
                if (available < needed) {
                    this.dialog.add(AlertDialog, {
                        title: _t('🛑 Sotuv taqiqlandi'),
                        body: _t(
                            `Mahsulot: ${product.display_name}\n\n` +
                            `📍 Ombor: ${wh_name}\n` +
                            `📦 Ombor qoldig'i: ${available} ta\n` +
                            `🛒 Kerakli miqdor: ${needed} ta\n\n` +
                            `Ombor qoldig'i yetarli emas!`
                        ),
                    });
                    return;
                }
            }
        }

        await super.pay();
    },
});