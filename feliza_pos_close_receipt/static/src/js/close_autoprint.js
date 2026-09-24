/** Kassa yopilganda "Kassa yopish cheki" ni AVTOMAT chiqaradi.
 *  closeSession() sessiyani serverda yopadi va oxirida router.close() bilan
 *  POS'dan chiqadi. Biz router.close() dan OLDIN (DB yangilangach —
 *  sanalgan naxt/farq allaqachon yozilgan) hisobotni chiqaramiz. */
import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";

patch(ClosePosPopup.prototype, {
    async closeSession() {
        const sessionId = this.pos.session.id;
        const router = this.pos.router;
        const origClose = router.close.bind(router);
        const self = this;
        let handled = false;
        router.close = async function (...args) {
            if (!handled) {
                handled = true;
                try {
                    await self.report.doAction(
                        "feliza_pos_close_receipt.action_report_pos_close",
                        [sessionId]
                    );
                } catch (e) {
                    // Chek chiqmasa ham kassa yopilaveradi — xatoni yutamiz.
                    console.warn("Kassa yopish cheki chiqmadi:", e);
                }
            }
            router.close = origClose;
            return origClose(...args);
        };
        try {
            return await super.closeSession(...arguments);
        } finally {
            router.close = origClose;
        }
    },
});
