/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class InventoryScanField extends Component {
    static template = "feliza_inventory.InventoryScan";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.inputRef = useRef("scanInput");

        // Boshqa oyna/tabga chiqib qaytilganda skaner maydoni fokusni
        // yo'qotadi -> skaner tugmalari bo'shga ketadi. Fokusni ushlab
        // turamiz: (1) oyna qaytganda, (2) davriy tekshiruv bilan.
        this._onWinFocus = () => this._maybeRefocus();
        this._onVisible = () => { if (!document.hidden) this._maybeRefocus(); };
        this._keepFocus = () => this._maybeRefocus();

        // "Sanalgan" (son tuzatish) inputiga yoki mahsulot ro'yxatiga fokus
        // tushganini kuzatamiz — skaner fokusni O'G'IRLAB, yozilgan raqamni
        // barkod maydoniga tushirib yubormasligi uchun.
        this._lastCountFocus = 0;
        this._onDocFocusIn = (ev) => {
            const t = ev.target;
            if (t && t.closest &&
                t.closest(".fz_count_edit, .fz_scan_panel .o_list_table")) {
                this._lastCountFocus = Date.now();
            }
        };

        onMounted(() => {
            this.focus();
            window.addEventListener("focus", this._onWinFocus);
            document.addEventListener("visibilitychange", this._onVisible);
            document.addEventListener("focusin", this._onDocFocusIn);
            // Har ~0.7s: fokus "bo'sh" bo'lsa skaner maydoniga qaytaramiz
            // (boshqa input/tugma/dialog/son-tuzatishda bo'lsa TEGMAYMIZ).
            this._focusTimer = setInterval(this._keepFocus, 700);
        });
        onWillUnmount(() => {
            window.removeEventListener("focus", this._onWinFocus);
            document.removeEventListener("visibilitychange", this._onVisible);
            document.removeEventListener("focusin", this._onDocFocusIn);
            if (this._focusTimer) {
                clearInterval(this._focusTimer);
            }
        });
    }

    /** Fokus hech narsada (yoki body'да) bo'lsa — skaner maydoniga qaytaramiz.
     *  Foydalanuvchi boshqa input/tugma/ochilgan oynada ishlayotgan bo'lsa
     *  aralashmaymiz. */
    _maybeRefocus() {
        const el = this.inputRef.el;
        if (!el || document.hidden) {
            return;
        }
        const active = document.activeElement;
        if (active === el) {
            return;
        }
        // Ustma-ust oyna (dialog/modal) OCHIQ bo'lsa — skaner fokusni umuman
        // olmasin (user "To'liq qidiruv" oynasida yoki boshqa dialogda).
        if (document.querySelector(".o_dialog, .modal.show, .modal.in")) {
            return;
        }
        // "Sanalgan" son tuzatish yaqinda (1.5s) fokusda bo'lgan bo'lsa —
        // TEGMAYMIZ (reload/qayta-render orasidagi bo'sh onni ushlaydi, aks
        // holda yozilgan raqam barkod maydoniga tushib ketadi).
        if (Date.now() - this._lastCountFocus < 1500) {
            return;
        }
        const tag = active && active.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" ||
            tag === "BUTTON" || tag === "A") {
            return;
        }
        // Dialog / mahsulot ro'yxati / son-tuzatish ичида bo'lsa tegmaymiz
        if (active && active.closest &&
            active.closest(".modal, .o_dialog, .o_technical_modal, " +
                           ".fz_scan_panel, .fz_count_edit")) {
            return;
        }
        this.focus();
    }

    focus() {
        if (this.inputRef.el) {
            // preventScroll: fokus olganda oyna TEPAGA sakramasin (asosiy muammo)
            this.inputRef.el.focus({ preventScroll: true });
            this.inputRef.el.select();
        }
    }

    /** Formaning skroll konteyneri (o'rin saqlash uchun). */
    _scrollEl() {
        const el = this.inputRef.el;
        return (el && el.closest(".o_content"))
            || document.querySelector(".o_action_manager .o_content")
            || document.querySelector(".o_content");
    }

    /** Ovoz: to'g'ri = yuqori "biip", xato = past "err" tovushi.
     *  Web Audio — tashqi fayl kerak emas. */
    _beep(ok) {
        try {
            const AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) { return; }
            const ctx = this._audio || (this._audio = new AC());
            if (ctx.state === "suspended") { ctx.resume(); }
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            gain.gain.setValueAtTime(0.0001, now);
            if (ok) {
                // BALAND, aniq eshitiladigan yuqori signal
                osc.type = "square";
                osc.frequency.setValueAtTime(1500, now);
                gain.gain.exponentialRampToValueAtTime(0.6, now + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.16);
                osc.start(now);
                osc.stop(now + 0.17);
            } else {
                // past, uzun "buzz" xato signal (ikki bo'lak)
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(200, now);
                osc.frequency.setValueAtTime(140, now + 0.18);
                gain.gain.exponentialRampToValueAtTime(0.6, now + 0.01);
                gain.gain.setValueAtTime(0.6, now + 0.32);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);
                osc.start(now);
                osc.stop(now + 0.46);
            }
        } catch (e) { /* ovoz ishlamasa ham skan davom etadi */ }
    }

    async onKeydown(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        const el = this.inputRef.el;
        const code = (el.value || "").trim();
        el.value = "";
        if (!code) {
            return;
        }
        const rec = this.props.record;
        if (!rec.resId) {
            this.notification.add("Avval sessiyani boshlang", { type: "warning" });
            return;
        }
        let res;
        try {
            res = await this.orm.call(
                "feliza.inventory.session", "scan_barcode", [[rec.resId], code]);
        } catch (e) {
            this._beep(false);
            this.notification.add("Xatolik: " + code, { type: "danger" });
            this.focus();
            return;
        }
        if (res && res.ok) {
            this._beep(true);
            if (res.type === "location") {
                this.notification.add("📍 Joy: " + res.name, { type: "info" });
            } else {
                this.notification.add(
                    "✅ " + res.name + "  →  " + res.counted, { type: "success" });
            }
            // Formani yangilashда oyna joyida qolsin (tepaga sakramasin)
            const sc = this._scrollEl();
            const top = sc ? sc.scrollTop : 0;
            try {
                await rec.load();
            } catch (e) {
                // reload muvaffaqiyatsiz bo'lsa ham skaner davom etadi
            }
            if (sc) {
                sc.scrollTop = top;
                requestAnimationFrame(() => { sc.scrollTop = top; });
            }
        } else {
            this._beep(false);
            this.notification.add(
                "⛔ " + ((res && res.message) || ("Topilmadi: " + code)),
                { type: "danger", sticky: false });
        }
        this.focus();
    }
}

export const inventoryScanField = {
    component: InventoryScanField,
    supportedTypes: ["char"],
};

registry.category("fields").add("inventory_scan", inventoryScanField);


/**
 * "Sanalgan"ni INLINE tahrirlash — popup YO'Q, o'zgartirib chiqilganda
 * DARHOL saqlanadi. To'g'ridan-to'g'ri model metodini (action_set_counted)
 * chaqiradi (SQL-view ni ham, javon qatorini ham qo'llab-quvvatlaydi).
 */
export class InvCountField extends Component {
    static template = "feliza_inventory.InvCountField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.inputRef = useRef("countInput");
        this._saving = false;
    }

    get displayValue() {
        const v = this.props.record.data[this.props.name];
        return v === undefined || v === null ? 0 : v;
    }

    get readonly() {
        // Faqat "astatkaga qo'llangan" sessiyada readonly. props.readonly ga
        // QARAMAYMIZ — shunda HAR QATORDA doim tahrir-bulut turadi (Odoo
        // editable listda faqat tanlangan qator emas).
        return !!this.props.record.data.applied;
    }

    /** Bosilganda faqat tahrir — qatorni ochmasin, skaner aralashmasin.
     *  Fokus olib, mavjud sonni belgilaydi (darhol ustidan yozish uchun). */
    _onClick(ev) {
        ev.stopPropagation();
    }

    _onFocus(ev) {
        ev.stopPropagation();
        const el = this.inputRef.el;
        if (el) {
            el.select();
        }
    }

    /** Klaviatura hodisalari BU YERDA to'xtaydi — skaner maydoniga yoki
     *  ro'yxatga o'tib ketmaydi. Enter/Tab = saqlash, Escape = bekor. */
    _onKeydown(ev) {
        ev.stopPropagation();
        if (ev.key === "Enter" || ev.key === "Tab") {
            ev.preventDefault();
            this._save();
        } else if (ev.key === "Escape") {
            const el = this.inputRef.el;
            if (el) {
                el.value = this.displayValue;
                el.blur();
            }
        }
    }

    _onChangeEvt() {
        this._save();
    }

    async _save() {
        if (this._saving) {
            return;
        }
        const rec = this.props.record;
        const el = this.inputRef.el;
        if (!rec.resId || !el) {
            return;
        }
        const raw = String(el.value || "").replace(",", ".").trim();
        let v = parseFloat(raw);
        if (isNaN(v)) {
            v = 0;
        }
        if (Math.abs(v - this.displayValue) < 0.0001) {
            return;  // o'zgarmadi
        }
        this._saving = true;
        try {
            await this.orm.call(rec.resModel, "action_set_counted",
                                [[rec.resId], v]);
            this.notification.add("✓ Sanalgan: " + v, {
                type: "success", sticky: false });
        } catch (e) {
            const msg = (e && e.message && e.message.data
                && e.message.data.message) || "Saqlashda xatolik";
            this.notification.add(msg, { type: "danger" });
        }
        // Yig'indi/farq/holat qayta hisoblansin — ro'yxatni yangilaymiz,
        // oyna joyida qolsin.
        const sc = document.querySelector(".o_action_manager .o_content")
                 || document.querySelector(".o_content");
        const top = sc ? sc.scrollTop : 0;
        try {
            await rec.model.root.load();
        } catch (e) { /* ignore */ }
        if (sc) {
            requestAnimationFrame(() => { sc.scrollTop = top; });
        }
        this._saving = false;
    }
}

export const invCountField = {
    component: InvCountField,
    supportedTypes: ["float"],
};

registry.category("fields").add("inv_count", invCountField);


/**
 * "Javonlar" (joy) ustuni — BULUT ko'rinishida. Bosilganda tovarni boshqa
 * javonga KO'CHIRISH oynasini ochadi (shu omborning javonlaridan qidiruvli
 * tanlash). location_names (Char) ni ko'rsatadi.
 */
export class InvLocationField extends Component {
    static template = "feliza_inventory.InvLocationField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    }

    get displayValue() {
        return this.props.record.data[this.props.name] || "—";
    }

    get editable() {
        return !this.props.record.data.applied;
    }

    async onClick(ev) {
        ev.stopPropagation();
        if (!this.editable) {
            return;
        }
        const rec = this.props.record;
        if (!rec.resId) {
            return;
        }
        let act;
        try {
            act = await this.orm.call(rec.resModel, "action_edit_location",
                                      [[rec.resId]]);
        } catch (e) {
            const msg = (e && e.message && e.message.data
                && e.message.data.message) || "Xatolik";
            this.notification.add(msg, { type: "danger" });
            return;
        }
        if (act) {
            await this.action.doAction(act);
        }
    }
}

export const invLocationField = {
    component: InvLocationField,
    supportedTypes: ["char"],
};

registry.category("fields").add("inv_location", invLocationField);
