/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { useState, useRef, useEffect, onMounted, onWillUnmount } from "@odoo/owl";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { _t } from "@web/core/l10n/translation";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);

        this.qrState = useState({ scanning: false, error: null });
        this.videoRef  = useRef("qr-video");
        this.canvasRef = useRef("qr-canvas");

        this._mediaStream = null;
        this._rafId       = null;

        // ── Apparat skaner (keyboard-wedge) uchun bufer ──
        this._scanBuf     = "";
        this._scanLastTs  = 0;
        this._onHwKeydown = this._onHwKeydown.bind(this);

        // Kamera scanning = true bo'lganda ochiladi
        useEffect(
            () => {
                if (this.qrState.scanning) {
                    this._openCamera();
                }
                return () => this._stopCamera();
            },
            () => [this.qrState.scanning]
        );

        // Ekran ochiq turganda apparat skanerni global tinglaymiz
        onMounted(() => document.addEventListener("keydown", this._onHwKeydown, true));
        onWillUnmount(() => {
            document.removeEventListener("keydown", this._onHwKeydown, true);
            this._stopCamera();
        });
    },

    // ── Yordamchi ──────────────────────────────────────────

    cleanPhone(raw) {
        return (raw || "").replace(/[\s\-\(\)\.]/g, "");
    },

    _clearSearchBox() {
        try {
            if (this.searchInputRef && this.searchInputRef.el) {
                this.searchInputRef.el.value = "";
            }
            if (this.state) {
                this.state.query = "";
            }
        } catch (e) {
            /* e'tiborsiz */
        }
    },

    // ── Apparat skaner (barcode/QR aparad) ─────────────────
    // Skanerlar klaviatura kabi ishlaydi: belgilarni juda tez "terib",
    // oxirida Enter yuboradi. Tez ketma-ketlik + Enter = skaner o'qishi.
    _onHwKeydown(ev) {
        // Kamera ochiq bo'lsa, apparat skanerni tinglamaymiz
        if (this.qrState.scanning) {
            return;
        }
        const now = Date.now();
        const key = ev.key;

        if (key === "Enter" || key === "Tab") {
            const buf = this._scanBuf;
            this._scanBuf = "";
            // Kamida 4 belgi va oxirgi belgidan keyin tez (skaner) bo'lsa
            if (buf.length >= 4 && now - this._scanLastTs < 120) {
                ev.preventDefault();
                ev.stopPropagation();
                this._clearSearchBox();
                this.processQrScan(buf);
            }
            return;
        }

        // Faqat bitta belgili tugmalar (raqam, harf, +, . va h.k.)
        if (key && key.length === 1) {
            // Belgilar orasida 120ms dan ko'p tanaffus bo'lsa — bu qo'lda yozish,
            // buferni tozalaymiz (skaner belgilarni <50ms da yuboradi).
            if (now - this._scanLastTs > 120) {
                this._scanBuf = "";
            }
            this._scanBuf += key;
            this._scanLastTs = now;
        }
    },

    // ── Kamera boshqaruv ───────────────────────────────────

    startQrScan() {
        this.qrState.error   = null;
        this.qrState.scanning = true;
    },

    stopQrScan() {
        this._stopCamera();
        this.qrState.scanning = false;
        this.qrState.error   = null;
    },

    async _openCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } },
                audio: false,
            });
            this._mediaStream = stream;

            const video = this.videoRef.el;
            if (!video) {
                this._stopCamera();
                return;
            }
            video.srcObject = stream;
            await video.play();
            this._startScanLoop();
        } catch (err) {
            const msg =
                err.name === "NotAllowedError" || err.name === "PermissionDeniedError"
                    ? _t("Kamera ruxsati rad etildi. Brauzer sozlamalarida kamera ruxsatini bering.")
                    : _t("Kamera ochilmadi: %s", err.message);
            this.qrState.error   = msg;
            this.qrState.scanning = false;
        }
    },

    _stopCamera() {
        if (this._rafId) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
        }
        if (this._mediaStream) {
            this._mediaStream.getTracks().forEach((t) => t.stop());
            this._mediaStream = null;
        }
        const video = this.videoRef.el;
        if (video) {
            video.srcObject = null;
        }
    },

    _startScanLoop() {
        const video  = this.videoRef.el;
        const canvas = this.canvasRef.el;
        if (!video || !canvas) return;

        const ctx = canvas.getContext("2d", { willReadFrequently: true });

        const tick = () => {
            if (!this.qrState.scanning) return;

            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                canvas.width  = video.videoWidth;
                canvas.height = video.videoHeight;
                ctx.drawImage(video, 0, 0);

                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                // window.jsQR — static/lib/jsQR.js dan yuklangan global
                const code = window.jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert",
                });

                if (code && code.data) {
                    // QR topildi — kamerani to'xtatib qidiruv boshlash
                    this._stopCamera();
                    this.qrState.scanning = false;
                    this.processQrScan(code.data);
                    return;
                }
            }

            this._rafId = requestAnimationFrame(tick);
        };

        this._rafId = requestAnimationFrame(tick);
    },

    // ── Mijoz qidirish ─────────────────────────────────────

    async processQrScan(scanned) {
        const phone = this.cleanPhone(scanned);
        if (!phone) {
            return;
        }

        // 1. Yuklangan partnyorlar ichida qidirish
        const loaded = [...this.state.initialPartners, ...this.state.loadedPartners];
        let found = loaded.find(
            (p) => this.cleanPhone(p.phone) === phone || this.cleanPhone(p.mobile) === phone
        ) || null;

        // 2. POS keshidagi barcha partnyorlarda qidirish
        if (!found) {
            const hits = this.pos.models["res.partner"].filter(
                (p) => this.cleanPhone(p.phone) === phone || this.cleanPhone(p.mobile) === phone
            );
            found = hits[0] || null;
        }

        // 3. Serverdan qidirish (50 000+ kontakt, format normallashtirilgan)
        if (!found) {
            try {
                const result = await this.pos.data.callRelated(
                    "res.partner",
                    "pos_qr_search_partner",
                    [this.pos.config.id, scanned]
                );
                const partners = result["res.partner"] || [];
                // Aniq mos kelganini afzal ko'ramiz
                found =
                    partners.find(
                        (p) =>
                            this.cleanPhone(p.phone) === phone ||
                            this.cleanPhone(p.mobile) === phone
                    ) ||
                    partners[0] ||
                    null;
            } catch (e) {
                console.error("[QR] Server qidiruv xatosi:", e);
            }
        }

        if (found) {
            this.clickPartner(found);
        } else {
            this.notification.add(_t("Mijoz topilmadi: %s", scanned), { type: "warning" });
        }
    },
});
