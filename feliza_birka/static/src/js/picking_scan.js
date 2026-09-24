/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * QABUL HUJJATIDA INLINE SKANER — Enter (skaner) bosilganda barkodni
 * serverga yuboradi (stock.picking.feliza_scan_barcode), tovar qatorga
 * +1 qo'shiladi. Ovoz (biip) + bildirishnoma bilan.
 */
export class PickingScanField extends Component {
    static template = "feliza_birka.PickingScan";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.inputRef = useRef("scanInput");
        onMounted(() => this.focus());
    }

    focus() {
        if (this.inputRef.el) {
            this.inputRef.el.focus({ preventScroll: true });
            this.inputRef.el.select();
        }
    }

    _beep(ok) {
        try {
            const AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) { return; }
            const ctx = this._audio || (this._audio = new AC());
            if (ctx.state === "suspended") { ctx.resume(); }
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            gain.gain.setValueAtTime(0.0001, now);
            if (ok) {
                osc.type = "square";
                osc.frequency.setValueAtTime(1500, now);
                gain.gain.exponentialRampToValueAtTime(0.6, now + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.16);
                osc.start(now); osc.stop(now + 0.17);
            } else {
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(200, now);
                osc.frequency.setValueAtTime(140, now + 0.18);
                gain.gain.exponentialRampToValueAtTime(0.6, now + 0.01);
                gain.gain.setValueAtTime(0.6, now + 0.32);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);
                osc.start(now); osc.stop(now + 0.46);
            }
        } catch (e) { /* ovozsiz ham davom */ }
    }

    async onKeydown(ev) {
        if (ev.key !== "Enter") { return; }
        ev.preventDefault();
        ev.stopPropagation();
        const el = this.inputRef.el;
        const code = (el.value || "").trim();
        el.value = "";
        if (!code) { return; }

        const rec = this.props.record;
        // Yangi (saqlanmagan) hujjat bo'lsa — avval saqlaymiz (id kerak)
        if (!rec.resId) {
            try { await rec.save(); } catch (e) { /* pastda tekshiramiz */ }
            if (!rec.resId) {
                this._beep(false);
                this.notification.add("Avval hujjatni saqlang", {
                    type: "warning" });
                this.focus();
                return;
            }
        }

        let res;
        try {
            res = await this.orm.call(
                "stock.picking", "feliza_scan_barcode", [[rec.resId], code]);
        } catch (e) {
            this._beep(false);
            this.notification.add("Xatolik: " + code, { type: "danger" });
            this.focus();
            return;
        }

        if (res && res.ok) {
            this._beep(true);
            this.notification.add("✅ " + res.name + "  →  " + res.qty, {
                type: "success" });
            // qatorlar/hisoblagich yangilansin
            const sc = document.querySelector(".o_action_manager .o_content")
                     || document.querySelector(".o_content");
            const top = sc ? sc.scrollTop : 0;
            try { await rec.model.root.load(); } catch (e) { /* ignore */ }
            if (sc) { requestAnimationFrame(() => { sc.scrollTop = top; }); }
        } else {
            this._beep(false);
            this.notification.add(
                "⛔ " + ((res && res.message) || ("Topilmadi: " + code)),
                { type: "danger", sticky: false });
        }
        this.focus();
    }
}

export const pickingScanField = {
    component: PickingScanField,
    supportedTypes: ["char"],
};

registry.category("fields").add("feliza_picking_scan", pickingScanField);
