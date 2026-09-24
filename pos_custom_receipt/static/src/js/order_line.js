/**
 * Odoo 19 port.
 * 18 da narx matn ko'rinishida kelardi va regex bilan tozalanardi.
 * 19 da qator obyekti to'g'ridan-to'g'ri kelayapti, shuning uchun summa
 * aniq hisoblanadi: chegirmasiz summa − chegirmali summa.
 */
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { formatCurrency } from "@web/core/currency";

patch(Orderline.prototype, {
    /** Qatordagi chegirma summasi (valyuta formatida). Bo'lmasa — bo'sh satr. */
    get discountAmountStr() {
        const line = this.line;
        if (!line || !line.discount) {
            return "";
        }
        try {
            const amount = line.displayPriceNoDiscount - line.displayPrice;
            if (!amount || !isFinite(amount)) {
                return "";
            }
            return formatCurrency(line.currency.round(amount), line.currency.id);
        } catch {
            return "";
        }
    },
});
