/** @odoo-module **/
/*
 * Savdolar YO'QOLMASIN kafolati.
 * Odoo 19 POS'da yopishda sync bor, lekin tab yopilsa yoki internet uzilsa
 * buyurtmalar brauzer (IndexedDB) da qolib, keyingi kun boshqa smenaga
 * tushib qoladi. Bu qatlam:
 *   1) orqa fonda har 20s majburiy sinxron (pending + online bo'lsa),
 *   2) internet qaytganda darhol sinxron,
 *   3) tab yopilishida ogohlantirish (yuborilmagan savdo bo'lsa).
 */
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

const FZ_SYNC_INTERVAL = 20000; // 20 soniya

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this._fzStartSyncGuard();
    },

    /** Yuborilmagan (pending) buyurtma bormi? */
    _fzHasPending() {
        try {
            const po = this.pendingOrder || {};
            const c = po.create && po.create.size ? po.create.size : 0;
            const w = po.write && po.write.size ? po.write.size : 0;
            return c + w > 0;
        } catch (e) {
            return false;
        }
    },

    _fzOnline() {
        return typeof navigator === "undefined" || navigator.onLine !== false;
    },

    /** Majburiy sinxron — pending bo'lsa va online bo'lsa. */
    async _fzForceSync() {
        if (this._fzSyncing || !this._fzHasPending() || !this._fzOnline()) {
            return;
        }
        this._fzSyncing = true;
        try {
            await this.syncAllOrders({ force: true });
        } catch (e) {
            // offline/xato — keyingi urinishda qayta yuboriladi
        } finally {
            this._fzSyncing = false;
        }
    },

    _fzStartSyncGuard() {
        // 1) davriy majburiy sinxron
        this._fzSyncTimer = setInterval(() => this._fzForceSync(), FZ_SYNC_INTERVAL);

        // 2) internet qaytganda darhol
        this._fzOnlineHandler = () => this._fzForceSync();
        window.addEventListener("online", this._fzOnlineHandler);

        // 3) tab/oyna yopilishida ogohlantirish + best-effort sinxron
        this._fzBeforeUnload = (ev) => {
            if (this._fzHasPending()) {
                // fon sinxronni ham urinib ko'ramiz
                this._fzForceSync();
                ev.preventDefault();
                ev.returnValue =
                    "DIQQAT: yuborilmagan savdolar bor! Yopmang — avval " +
                    "hammasi serverga yuborilsin.";
                return ev.returnValue;
            }
        };
        window.addEventListener("beforeunload", this._fzBeforeUnload);
    },
});
