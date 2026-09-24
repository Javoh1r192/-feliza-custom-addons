/*
    Feliza POS Layout — interaktiv kassa panel o'lchagichi
    ======================================================
    Kassa (chap) panelning o'ng chekkasidan sichqoncha yoki BARMOQ (sensor ekran)
    bilan tortib, uning kengligini jonli o'zgartirish mumkin.

    - Tanlangan kenglik shu qurilma brauzerida eslab qolinadi (localStorage),
      POS qayta ochilganda ham saqlanadi.
    - Dastakni IKKI MARTA bosish -> standart kenglikka qaytaradi.
    - Tortayotganda joriy kenglik (px) ko'rsatiladi.
    - Mobil ko'rinishda (ekran < 993px) o'chirilgan.

    Eslatma: bu fayl Odoo modeli yoki template'ini o'zgartirmaydi — faqat
    brauzerdagi CSS o'zgaruvchisini (--feliza-leftpane-width) boshqaradi.
*/
(function () {
    "use strict";

    var STORAGE_KEY = "feliza_pos_leftpane_width";
    var MIN_WIDTH = 320;          // eng kichik ruxsat etilgan kenglik
    var MAX_WIDTH = 900;          // eng katta (ekranning 70% dan oshmaydi)
    var HANDLE_ZONE = 16;         // px — o'ng chekkadagi sezgir zona
    var MOBILE_BREAKPOINT = 993;  // bundan kichik ekranda o'chirilgan

    var rootStyle = document.documentElement.style;
    var dragging = false;
    var paneEl = null;
    var tooltip = null;

    function maxAllowed() {
        return Math.min(MAX_WIDTH, Math.round(window.innerWidth * 0.7));
    }

    function clamp(v) {
        return Math.max(MIN_WIDTH, Math.min(maxAllowed(), v));
    }

    function applyWidth(px) {
        rootStyle.setProperty("--feliza-leftpane-width", px + "px");
    }

    function getPane() {
        return document.querySelector(".product-screen .leftpane");
    }

    function inHandleZone(pane, e) {
        var rect = pane.getBoundingClientRect();
        return (
            e.clientX >= rect.right - HANDLE_ZONE &&
            e.clientX <= rect.right + HANDLE_ZONE &&
            e.clientY >= rect.top &&
            e.clientY <= rect.bottom
        );
    }

    // --- Jonli px ko'rsatkichi ---
    function showTooltip(px, x, y) {
        if (!tooltip) {
            tooltip = document.createElement("div");
            tooltip.className = "feliza-resize-tooltip";
            document.body.appendChild(tooltip);
        }
        tooltip.textContent = px + " px";
        tooltip.style.left = x + "px";
        tooltip.style.top = y + "px";
        tooltip.style.display = "block";
    }
    function hideTooltip() {
        if (tooltip) {
            tooltip.style.display = "none";
        }
    }

    // --- Saqlangan kenglikni tiklash ---
    function restore() {
        var saved = parseInt(window.localStorage.getItem(STORAGE_KEY), 10);
        if (saved && !isNaN(saved)) {
            applyWidth(clamp(saved));
        }
    }

    // --- Tortishni boshlash ---
    function onPointerDown(e) {
        if (window.innerWidth < MOBILE_BREAKPOINT) {
            return;
        }
        if (e.pointerType === "mouse" && e.button !== 0) {
            return; // faqat chap tugma
        }
        var pane = getPane();
        if (!pane || !inHandleZone(pane, e)) {
            return;
        }
        dragging = true;
        paneEl = pane;
        document.body.classList.add("feliza-resizing");
        try {
            pane.setPointerCapture(e.pointerId);
        } catch (err) {
            /* eski brauzerlar uchun — e'tiborsiz */
        }
        e.preventDefault();
    }

    function onPointerMove(e) {
        if (!dragging || !paneEl) {
            return;
        }
        var rect = paneEl.getBoundingClientRect();
        var w = clamp(Math.round(e.clientX - rect.left));
        applyWidth(w);
        showTooltip(w, e.clientX + 18, e.clientY + 18);
        e.preventDefault();
    }

    function endDrag() {
        if (!dragging) {
            return;
        }
        dragging = false;
        document.body.classList.remove("feliza-resizing");
        hideTooltip();
        var pane = paneEl || getPane();
        if (pane) {
            var w = clamp(Math.round(pane.getBoundingClientRect().width));
            window.localStorage.setItem(STORAGE_KEY, String(w));
        }
        paneEl = null;
    }

    // --- Ikki marta bosish: standart kenglikka qaytarish ---
    function onDblClick(e) {
        if (window.innerWidth < MOBILE_BREAKPOINT) {
            return;
        }
        var pane = getPane();
        if (!pane || !inHandleZone(pane, e)) {
            return;
        }
        window.localStorage.removeItem(STORAGE_KEY);
        rootStyle.removeProperty("--feliza-leftpane-width"); // CSS'dagi standartga qaytadi
        e.preventDefault();
    }

    // --- Ekran o'lchami o'zgarsa, kenglikni chegara ichida ushlash ---
    function onResize() {
        var saved = parseInt(window.localStorage.getItem(STORAGE_KEY), 10);
        if (saved && !isNaN(saved)) {
            applyWidth(clamp(saved));
        }
    }

    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("pointermove", onPointerMove, true);
    document.addEventListener("pointerup", endDrag, true);
    document.addEventListener("pointercancel", endDrag, true);
    document.addEventListener("dblclick", onDblClick, true);
    window.addEventListener("resize", onResize);

    restore();
})();
