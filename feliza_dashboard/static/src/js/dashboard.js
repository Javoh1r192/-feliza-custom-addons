/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";

/** Bir sahifadagi qator soni — Odoo'ning o'z jadvallaridagidek */
const PAGE_SIZE = 40;

/**
 * Ombor tafsiloti uchun serverdan olinadigan qator soni.
 * Sahifalash qo'shilgani uchun bu raqamni oshirsak ham brauzer
 * sekinlashmaydi — ekranda baribir 40 qator chiziladi.
 */
const DETAIL_LIMIT = 400;

const PERIODS = [
    { key: "today", label: "Bugun" },
    { key: "yesterday", label: "Kecha" },
    { key: "week", label: "Hafta" },
    { key: "month", label: "Oy" },
    { key: "quarter", label: "Chorak" },
    { key: "year", label: "Yil" },
];

/** Hafta kunlari — bir kun tanlanganda ko'rsatiladi */
const WEEKDAYS = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba",
                  "Payshanba", "Juma", "Shanba"];

/** "2026-08-21" ko'rinishidagi satrni Date'ga aylantiradi (mahalliy vaqtda) */
function isoToDate(iso) {
    const p = String(iso || "").split("-");
    if (p.length !== 3) return null;
    const d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
    return isNaN(d.getTime()) ? null : d;
}

function dateToIso(d) {
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${m}-${day}`;
}

export class FelizaDashboard extends Component {
    static template = "feliza_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.periods = PERIODS;
        this.tipRef = useRef("tip");

        this.state = useState({
            loading: true,
            error: "",
            tab: "today",
            period: "today",
            // Aniq sana tanlanganda to'ladi (period === "custom").
            // Server tomonda `_period_dates` shu ikkisini oladi.
            dateFrom: null,
            dateTo: null,
            // Serverdan qaytgan HAQIQIY davr — chipda shu ko'rsatiladi,
            // ya'ni ekrandagi sana har doim ma'lumot olingan sana bilan bir xil
            range: null,          // {from, to, key}
            picker: false,        // sana tanlash oynasi ochiqmi
            pickMode: "day",      // "day" | "range"
            pickFrom: "",
            pickTo: "",
            store: null,
            cfg: null,
            overview: null,
            staff: null,
            products: null,
            stock: null,
            discounts: null,
            transfers: null,
            trOpenId: null,      // ochilgan o'tkazma qatori (accordion)
            trDetail: null,      // yuklangan o'tkazma detali
            trLoading: false,
            kamomat: null,
            finance: null,
            sessions: null,
            salesList: null,
            stockStores: null,
            stockDetail: null,
            stockWh: null,
            stockWhName: "",
            stockQuery: "",
            stockOrder: "value",
            stockBusy: false,
            diagnostics: null,
            lastUpdate: "",
            modal: null,          // {kind: 'order'|'payment', data: {...}}
            modalLoading: false,
            // Sichqoncha ostidagi qalqib chiquvchi izoh (tooltip).
            // {x, y, title, rows:[{label, value, cls}], i} — i faqat grafik uchun.
            tip: null,
            // Jadval sahifalari: {jadval_kaliti: sahifa_raqami}
            pages: {},
        });

        // Yozuvga kirib qaytganda o'sha bo'lim va davr saqlanib qolsin
        const saved = this.props.state;
        if (saved && saved.tab) {
            Object.assign(this.state, {
                tab: saved.tab,
                period: saved.period || this.state.period,
                dateFrom: saved.dateFrom || null,
                dateTo: saved.dateTo || null,
                store: saved.store !== undefined ? saved.store : this.state.store,
                stockWh: saved.stockWh || null,
                stockWhName: saved.stockWhName || "",
            });
        }
        useSetupAction({
            getLocalState: () => ({
                tab: this.state.tab,
                period: this.state.period,
                dateFrom: this.state.dateFrom,
                dateTo: this.state.dateTo,
                store: this.state.store,
                stockWh: this.state.stockWh,
                stockWhName: this.state.stockWhName,
            }),
        });

        onWillStart(async () => {
            try {
                this.state.cfg = await this.orm.call("feliza.dashboard", "get_config", []);
                // foydalanuvchiga ruxsat etilmagan bo'lim ochilib qolmasin
                if (this.state.cfg.tabs
                        && this.state.cfg.tabs.indexOf(this.state.tab) === -1) {
                    this.state.tab = this.state.cfg.default_tab || "stock";
                }
                await this.load();
            } catch (e) {
                this.state.error = (e && e.message && e.message.data
                    && e.message.data.message) || String(e);
                this.state.loading = false;
            }
            // har 3 daqiqada yangilanadi
            this._timer = setInterval(() => {
                if (!this.state.loading) {
                    this.load(true);
                }
            }, 180000);
        });

        onWillUnmount(() => {
            if (this._timer) {
                clearInterval(this._timer);
            }
        });
    }

    // ------------------------------------------------------------------ //
    get showCost() {
        return !!(this.state.cfg && this.state.cfg.show_cost);
    }
    get isManager() {
        return !!(this.state.cfg && this.state.cfg.is_manager);
    }
    get isStockOnly() {
        const c = this.state.cfg;
        return !!(c && c.is_stock && !c.is_manager && !c.is_store);
    }
    hasTab(key) {
        const c = this.state.cfg;
        return !c || !c.tabs || c.tabs.indexOf(key) !== -1;
    }
    /**
     * Ombor qoldig'i va diagnostika DAVRGA bog'liq emas — o'sha bo'limlarda
     * davr tugmalari ishlamaydi, shuning uchun ularni ko'rsatmaymiz
     * (ishlamaydigan filtr — chalg'ituvchi filtr).
     */
    get usesPeriod() {
        return this.state.tab !== "stock" && this.state.tab !== "diag";
    }

    // ------------------------------------------------------------------ //
    async load(silent = false) {
        if (!silent) {
            this.state.loading = true;
        }
        this.state.error = "";
        const args = [...this.periodArgs, this.state.store];
        try {
            if (this.state.tab === "today" || this.state.tab === "stores") {
                this.state.overview = await this.orm.call(
                    "feliza.dashboard", "get_overview", args);
                if (this.state.tab === "stores") {
                    this.state.sessions = await this.orm.call(
                        "feliza.dashboard", "get_sessions", args);
                }
            } else if (this.state.tab === "sales") {
                await this.loadSales();
            } else if (this.state.tab === "staff") {
                this.state.staff = await this.orm.call(
                    "feliza.dashboard", "get_staff", args);
            } else if (this.state.tab === "products") {
                this.state.products = await this.orm.call(
                    "feliza.dashboard", "get_products", args);
            } else if (this.state.tab === "fin") {
                this.state.finance = await this.orm.call(
                    "feliza.dashboard", "get_finance", args);
            } else if (this.state.tab === "transfer") {
                this.state.transfers = await this.orm.call(
                    "feliza.dashboard", "get_transfers", args);
            } else if (this.state.tab === "kam") {
                this.state.kamomat = await this.orm.call(
                    "feliza.dashboard", "get_kamomat", args);
            } else if (this.state.tab === "zakup") {
                this.state.zakup = await this.orm.call(
                    "feliza.dashboard", "get_zakup", args);
            } else if (this.state.tab === "zsales") {
                await this.loadZSales();
            } else if (this.state.tab === "zstock") {
                await this.loadZStock();
            } else if (this.state.tab === "zincome") {
                await this.loadZIncome();
            } else if (this.state.tab === "disc") {
                this.state.discounts = await this.orm.call(
                    "feliza.dashboard", "get_discounts", args);
            } else if (this.state.tab === "stock") {
                this.state.stock = await this.orm.call(
                    "feliza.dashboard", "get_stock", [this.state.store]);
                this.state.stockStores = await this.orm.call(
                    "feliza.dashboard", "get_stock_by_store", [this.state.store]);
                if (this.state.stockWh) {
                    await this.loadStockDetail();
                }
            } else if (this.state.tab === "diag") {
                this.state.diagnostics = await this.orm.call(
                    "feliza.dashboard", "get_diagnostics", []);
            }
            this._syncRange();
            this.state.lastUpdate = new Date().toLocaleTimeString("ru-RU", {
                hour: "2-digit", minute: "2-digit" });
        } catch (e) {
            this.state.error = (e && e.message && e.message.data
                && e.message.data.message) || String(e);
        }
        this.state.loading = false;
    }

    /**
     * Ekrandagi sana yozuvi — TAXMIN emas, serverdan qaytgan haqiqiy davr.
     * Server do'kon vaqt mintaqasi bilan ishlaydi, brauzer esa boshqa
     * mintaqada bo'lishi mumkin; shuning uchun sanani o'zimiz hisoblamaymiz.
     */
    _syncRange() {
        const s = this.state;
        const src = [s.overview, s.staff, s.products, s.discounts,
                     s.transfers, s.kamomat, s.finance, s.sessions,
                     s.zakup, s.zsales, s.zincome, s.salesList];
        for (const d of src) {
            if (d && d.period && d.period.from) {
                s.range = d.period;
                return;
            }
        }
        // Ombor bo'limi davrga bog'liq emas — o'sha yerda chip ham kerak emas
        if (s.period === "custom" && s.dateFrom) {
            s.range = { from: s.dateFrom, to: s.dateTo || s.dateFrom,
                        key: "custom" };
        }
    }

    // ------------------------------------------------------------------ //
    //  ZAKUPCHI STATISTIKASI (Sotuvlarim / Skladim / Daromadim)            //
    //  Filtrlar o'zgarganda faqat o'z bo'limi qayta so'raladi; yozish      //
    //  paytida serverni bombardimon qilmaslik uchun 350ms kutish bor.      //
    // ------------------------------------------------------------------ //
    get zFilters() {
        if (!this.state.z) {
            this.state.z = {
                who: "",                      // rahbar tanlagan zakupchi
                sStatus: "top", sQ: "", sCat: "", sColor: "", sSize: "",
                wStatus: "low", wQ: "",
                iQ: "",
            };
        }
        return this.state.z;
    }

    async loadZSales() {
        const z = this.zFilters;
        this.state.zsales = await this.orm.call(
            "feliza.dashboard", "get_zakupchi_sales",
            [...this.periodArgs, z.sStatus, z.sQ, z.sCat, z.sColor,
             z.sSize, z.who || null]);
    }
    async loadZStock() {
        const z = this.zFilters;
        this.state.zstock = await this.orm.call(
            "feliza.dashboard", "get_zakupchi_stock",
            [z.wStatus, z.wQ, z.who || null]);
    }
    async loadZIncome() {
        const z = this.zFilters;
        this.state.zincome = await this.orm.call(
            "feliza.dashboard", "get_zakupchi_income",
            [...this.periodArgs, z.iQ, z.who || null]);
    }
    zSet(maydon, qiymat, qayta) {
        this.zFilters[maydon] = qiymat;
        // filtr o'zgardi — sahifa boshidan
        this.pgReset(qayta === "sales" ? "zsales"
                     : qayta === "stock" ? "zstock" : null);
        clearTimeout(this._zTimer);
        this._zTimer = setTimeout(async () => {
            this.state.loading = true;
            try {
                if (qayta === "sales") await this.loadZSales();
                else if (qayta === "stock") await this.loadZStock();
                else if (qayta === "income") await this.loadZIncome();
                else await this.load(true);
            } catch (e) {
                this.state.error = String(e);
            }
            this.state.loading = false;
        }, 350);
    }
    async zSetWho(qiymat) {
        this.zFilters.who = qiymat;
        await this.load();
    }

    // ------------------------------------------------------------------ //
    //  SOTUVLAR RO'YXATI (kassa/do'kon bo'yicha to'liq, qator darajasida)  //
    // ------------------------------------------------------------------ //
    get salesFilters() {
        if (!this.state.sf) {
            this.state.sf = { q: "", seller: "" };
        }
        return this.state.sf;
    }
    isSalesSeller(id) {
        return String(id) === String(this.salesFilters.seller || "");
    }
    async loadSales() {
        const f = this.salesFilters;
        this.state.salesList = await this.orm.call(
            "feliza.dashboard", "get_sales_list",
            [...this.periodArgs, this.state.store, f.q, f.seller || null, 1000]);
    }
    onSalesQuery(ev) {
        this.salesFilters.q = ev.target.value || "";
        this.pgReset("sales");
        clearTimeout(this._salesTimer);
        this._salesTimer = setTimeout(async () => {
            this.state.loading = true;
            try { await this.loadSales(); }
            catch (e) { this.state.error = String(e); }
            this.state.loading = false;
        }, 350);
    }
    async setSalesSeller(ev) {
        this.salesFilters.seller = ev.target.value || "";
        this.pgReset("sales");
        this.state.loading = true;
        try { await this.loadSales(); }
        catch (e) { this.state.error = String(e); }
        this.state.loading = false;
    }
    async exportSales() {
        try {
            const f = this.salesFilters;
            const act = await this.orm.call(
                "feliza.dashboard", "export_sales_xlsx",
                [...this.periodArgs, this.state.store, f.q, f.seller || null]);
            await this.action.doAction(act);
        } catch (e) {
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
    }
    async exportStaff(which) {
        try {
            const act = await this.orm.call(
                "feliza.dashboard", "export_staff_xlsx",
                [...this.periodArgs, this.state.store, which || "both"]);
            await this.action.doAction(act);
        } catch (e) {
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
    }

    // O'tkazma qatoriga bosilganda — detalni ichma-ich ochish/yopish
    async toggleTransfer(id) {
        if (this.state.trOpenId === id) {
            this.state.trOpenId = null;
            this.state.trDetail = null;
            return;
        }
        this.state.trOpenId = id;
        this.state.trDetail = null;
        this.state.trLoading = true;
        try {
            this.state.trDetail = await this.orm.call(
                "feliza.dashboard", "get_transfer_detail", [id]);
        } catch (e) {
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
            this.state.trOpenId = null;
        } finally {
            this.state.trLoading = false;
        }
    }
    async exportTransfer(id) {
        try {
            const act = await this.orm.call(
                "feliza.dashboard", "export_transfer_xlsx", [id]);
            await this.action.doAction(act);
        } catch (e) {
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
    }

    // Daromad grafigi — SVG chiziq
    get ziDaily() {
        return (this.state.zincome && this.state.zincome.daily) || [];
    }
    get ziMax() {
        return Math.max(1, ...this.ziDaily.map((d) => d.amount));
    }
    get ziPath() {
        const rows = this.ziDaily;
        if (rows.length < 2) return "";
        const w = 640, h = 170, max = this.ziMax;
        const step = (w - 4) / (rows.length - 1);
        return rows.map((r, i) => (i ? "L" : "M")
            + (2 + i * step).toFixed(1) + ","
            + (h - 4 - (r.amount / max) * (h - 12)).toFixed(1)).join(" ");
    }
    get ziArea() {
        const p = this.ziPath;
        if (!p) return "";
        return p + " L638,166 L2,166 Z";
    }

    async setTab(tab) {
        this.state.tab = tab;
        this.pgReset();          // yangi bo'limda sahifa boshidan
        await this.load();
    }
    async setPeriod(p) {
        this.state.period = p;
        this.state.dateFrom = null;
        this.state.dateTo = null;
        this.state.picker = false;
        this.pgReset();
        await this.load();
    }

    // ------------------------------------------------------------------ //
    //  SANA TANLASH                                                        //
    //                                                                      //
    //  Tayyor davrlar (Bugun/Hafta/Oy...) ko'p hollarda yetarli, lekin
    //  «o'tgan shanba qancha savdo bo'ldi?» degan savolga javob bermaydi.
    //  Shuning uchun: bitta kun yoki ixtiyoriy oraliq tanlash mumkin,
    //  bitta kun tanlanganda esa ‹ › tugmalari bilan kundan kunga
    //  o'tib chiqiladi — har safar oynani qayta ochish shart emas.
    // ------------------------------------------------------------------ //
    get periodArgs() {
        return this.state.period === "custom" && this.state.dateFrom
            ? ["custom", this.state.dateFrom,
               this.state.dateTo || this.state.dateFrom]
            : [this.state.period, null, null];
    }

    get isCustom() {
        return this.state.period === "custom" && !!this.state.dateFrom;
    }

    /** Bitta kun tanlanganmi (‹ › tugmalari shunda ko'rinadi) */
    get isOneDay() {
        return this.isCustom
            && (!this.state.dateTo || this.state.dateTo === this.state.dateFrom);
    }

    /** Brauzerdagi bugungi sana — kalendarda kelajakni tanlab bo'lmasin */
    get maxDate() {
        return dateToIso(new Date());
    }

    fmtDate(iso, withYear = true) {
        const d = isoToDate(iso);
        if (!d) return "—";
        const s = `${String(d.getDate()).padStart(2, "0")}.`
                + `${String(d.getMonth() + 1).padStart(2, "0")}`;
        return withYear ? `${s}.${d.getFullYear()}` : s;
    }

    weekday(iso) {
        const d = isoToDate(iso);
        return d ? WEEKDAYS[d.getDay()] : "";
    }

    /** Filtr chipidagi yozuv: "21.08.2026" yoki "01.08 — 21.08.2026" */
    get rangeLabel() {
        const r = this.state.range;
        if (!r || !r.from) return "";
        if (r.from === r.to) return this.fmtDate(r.from);
        return `${this.fmtDate(r.from, false)} — ${this.fmtDate(r.to)}`;
    }

    get rangeDays() {
        const r = this.state.range;
        const a = r && isoToDate(r.from);
        const b = r && isoToDate(r.to);
        if (!a || !b) return 0;
        return Math.round((b - a) / 86400000) + 1;
    }

    togglePicker() {
        const s = this.state;
        if (s.picker) {
            s.picker = false;
            return;
        }
        // oyna ochilganda joriy davrdan boshlaydi
        const r = s.range || {};
        s.pickFrom = s.dateFrom || r.from || this.maxDate;
        s.pickTo = s.dateTo || r.to || s.pickFrom;
        s.pickMode = (s.pickFrom === s.pickTo) ? "day" : "range";
        s.picker = true;
    }

    setPickMode(mode) {
        this.state.pickMode = mode;
        if (mode === "day") {
            this.state.pickTo = this.state.pickFrom;
        }
    }

    onPickFrom(ev) {
        this.state.pickFrom = ev.target.value;
        if (this.state.pickMode === "day"
                || !this.state.pickTo
                || this.state.pickTo < this.state.pickFrom) {
            this.state.pickTo = this.state.pickFrom;
        }
    }
    onPickTo(ev) {
        this.state.pickTo = ev.target.value;
    }

    get pickValid() {
        const { pickFrom, pickTo, pickMode } = this.state;
        if (!pickFrom) return false;
        if (pickMode === "range" && (!pickTo || pickTo < pickFrom)) return false;
        return true;
    }

    async applyPick() {
        if (!this.pickValid) return;
        const s = this.state;
        await this.applyDates(s.pickFrom,
                              s.pickMode === "day" ? s.pickFrom : s.pickTo);
    }

    async applyDates(from, to) {
        const s = this.state;
        s.period = "custom";
        s.dateFrom = from;
        s.dateTo = to || from;
        s.picker = false;
        this.pgReset();
        await this.load();
    }

    /** Bir kun tanlanganda oldingi/keyingi kunga o'tish */
    async shiftDay(delta) {
        const base = isoToDate(this.state.dateFrom
                               || (this.state.range && this.state.range.from));
        if (!base) return;
        base.setDate(base.getDate() + delta);
        const iso = dateToIso(base);
        if (iso > this.maxDate) return;      // kelajakka o'tmaymiz
        await this.applyDates(iso, iso);
    }

    get canNextDay() {
        const cur = this.state.dateFrom
                    || (this.state.range && this.state.range.from);
        return !!cur && cur < this.maxDate;
    }
    async setStore(ev) {
        this.state.store = ev.target.value || null;
        this.pgReset();
        await this.load();
    }

    // ------------------------------------------------------------------ //
    //  Formatlash                                                         //
    // ------------------------------------------------------------------ //
    money(v) {
        if (v === null || v === undefined) return "—";
        const n = Number(v);
        if (!isFinite(n)) return "—";
        // To'liq summa (oxirgi so'mgacha), bo'sh joy bilan ajratilgan
        return Math.round(n).toLocaleString("ru-RU");
    }
    num(v, d = 0) {
        if (v === null || v === undefined) return "—";
        const n = Number(v);
        if (!isFinite(n)) return "—";
        return n.toLocaleString("ru-RU", {
            minimumFractionDigits: d, maximumFractionDigits: d });
    }
    pct(v, d = 1) {
        if (v === null || v === undefined) return "—";
        const n = Number(v);
        if (!isFinite(n)) return "—";
        return n.toFixed(d).replace(".", ",") + "%";
    }
    delta(v) {
        if (v === null || v === undefined) return "";
        const n = Number(v);
        if (!isFinite(n)) return "";
        return (n >= 0 ? "▲ " : "▼ ") + Math.abs(n).toFixed(1).replace(".", ",") + "%";
    }
    deltaClass(v) {
        if (v === null || v === undefined) return "fd-muted";
        return Number(v) >= 0 ? "fd-up" : "fd-dn";
    }
    planClass(p) {
        if (p === null || p === undefined) return "";
        if (p >= 100) return "fd-ok";
        if (p >= 85) return "fd-warn";
        return "fd-bad";
    }
    barWidth(v, max) {
        if (!max) return "0%";
        return Math.max(0, Math.min(100, (v / max) * 100)) + "%";
    }

    // ------------------------------------------------------------------ //
    //  Sahifalash (Odoo'nikiga o'xshash pager)                            //
    //
    //  Uzun jadval brauzerni sekinlashtiradi: 100+ qator uchun 100+ DOM
    //  daraxti quriladi va har bir qayta chizishda hammasi solishtiriladi.
    //  Shuning uchun jadvallar 40 qatordan sahifalanadi — ma'lumot
    //  serverdan baribir to'liq kelgani uchun sahifa almashishi bir
    //  zumda bo'ladi, qo'shimcha so'rov yubormaydi.
    // ------------------------------------------------------------------ //

    /** joriy sahifa raqami (0 dan) */
    pg(key) {
        return this.state.pages[key] || 0;
    }
    /** jadval nechta sahifaga bo'linadi */
    pgCount(rows) {
        const n = (rows || []).length;
        return Math.max(1, Math.ceil(n / PAGE_SIZE));
    }
    /** shu sahifaga tushadigan qatorlar */
    pgRows(rows, key) {
        rows = rows || [];
        if (rows.length <= PAGE_SIZE) return rows;
        // ro'yxat qisqarib ketgan bo'lsa (qidiruv, filtr) — boshiga qaytamiz
        let p = this.pg(key);
        const last = this.pgCount(rows) - 1;
        if (p > last) {
            p = last;
            this.state.pages[key] = p;
        }
        return rows.slice(p * PAGE_SIZE, p * PAGE_SIZE + PAGE_SIZE);
    }
    /** "41-80 / 152" */
    pgLabel(rows, key) {
        const n = (rows || []).length;
        const p = this.pg(key);
        const from = n ? p * PAGE_SIZE + 1 : 0;
        const to = Math.min(n, (p + 1) * PAGE_SIZE);
        return from + "-" + to + " / " + this.num(n);
    }
    pgPrev(key) {
        this.state.pages[key] = Math.max(0, this.pg(key) - 1);
    }
    pgNext(key, rows) {
        this.state.pages[key] = Math.min(this.pgCount(rows) - 1, this.pg(key) + 1);
    }
    /** filtr/qidiruv/davr o'zgarganda sahifani boshiga qaytaramiz */
    pgReset(key = null) {
        if (key) {
            this.state.pages[key] = 0;
        } else {
            this.state.pages = {};
        }
    }

    // ------------------------------------------------------------------ //
    //  Qalqib chiquvchi izoh (tooltip)                                    //
    //                                                                     //
    //  Qoida: tooltip QO'SHIMCHA ma'lumot beradi, yagona manba emas —     //
    //  har bir raqam jadvalda yoki yorliqda baribir ko'rinib turadi.      //
    //  Matn faqat t-esc orqali qo'yiladi (XSS'ga yo'l yo'q).              //
    // ------------------------------------------------------------------ //

    /** Ekran chetidan chiqib ketmasligi uchun joyni to'g'rilaymiz */
    _tipPos(ev) {
        const w = window.innerWidth, h = window.innerHeight;
        let x = ev.clientX + 16, y = ev.clientY + 16;
        if (x > w - 280) x = ev.clientX - 268;
        if (y > h - 170) y = Math.max(8, ev.clientY - 160);
        return { x, y };
    }

    /**
     * TEZLIK: sichqoncha harakatida butun panelni qayta chizmaymiz.
     * Joylashuv to'g'ridan-to'g'ri DOM'ga yoziladi; `state` esa faqat
     * izoh MAZMUNI o'zgarganda (boshqa ustun / boshqa soat) yangilanadi.
     */
    _moveTipEl(ev) {
        const el = this.tipRef && this.tipRef.el;
        if (!el) return;
        const p = this._tipPos(ev);
        el.style.left = p.x + "px";
        el.style.top = p.y + "px";
    }

    _sameTip(t, title, rows, i) {
        return t && t.i === i && t.title === title
            && t.rows.length === rows.length
            && t.rows.every((r, k) => r.label === rows[k].label && r.value === rows[k].value);
    }

    /** Ustun / qator ustiga kelganda */
    showTip(ev, title, rows) {
        rows = rows || [];
        if (this._sameTip(this.state.tip, title, rows, null)) {
            this._moveTipEl(ev);     // faqat siljish — render yo'q
            return;
        }
        const p = this._tipPos(ev);
        this.state.tip = { x: p.x, y: p.y, title, rows, i: null };
    }
    hideTip() {
        if (this.state.tip) this.state.tip = null;
    }

    // ------------------------------------------------------------------ //
    //  Ichiga kirish (drill-down)                                         //
    // ------------------------------------------------------------------ //
    async open(kind, recId = null, model = null) {
        // Chek va to'lov turi — panel ichida ochiladi (Odoo huquqi talab qilinmaydi)
        if (kind === "order") {
            return this.openOrder(recId);
        }
        if (kind === "payment") {
            return this.openPayment(recId);
        }
        if (kind === "store") {
            return this.openStore(recId);
        }
        if (kind === "session") {
            return this.openSession(recId);
        }
        try {
            const act = await this.orm.call("feliza.dashboard", "open_view",
                [kind, recId, ...this.periodArgs, this.state.store, model]);
            await this.action.doAction(act);
        } catch (e) {
            const msg = (e && e.message && e.message.data
                && e.message.data.message) || String(e);
            this.notification.add(msg, { type: "warning" });
        }
    }

    async openFinance(kind, key = null) {
        try {
            const act = await this.orm.call("feliza.dashboard", "open_finance",
                [kind, key, ...this.periodArgs]);
            await this.action.doAction(act);
        } catch (e) {
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
    }

    async openOrder(orderId) {
        this.state.modalLoading = true;
        this.state.modal = { kind: "order", data: null };
        try {
            const data = await this.orm.call(
                "feliza.dashboard", "get_order_detail", [orderId]);
            this.state.modal = { kind: "order", data };
        } catch (e) {
            this.state.modal = null;
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
        this.state.modalLoading = false;
    }

    async openPayment(methodId) {
        this.state.modalLoading = true;
        this.state.modal = { kind: "payment", data: null };
        try {
            const data = await this.orm.call(
                "feliza.dashboard", "get_payment_detail",
                [methodId, ...this.periodArgs, this.state.store]);
            this.state.modal = { kind: "payment", data };
        } catch (e) {
            this.state.modal = null;
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
        this.state.modalLoading = false;
    }

    async openStore(store) {
        this.state.modalLoading = true;
        this.state.modal = { kind: "store", data: null };
        try {
            const data = await this.orm.call(
                "feliza.dashboard", "get_store_detail",
                [store, ...this.periodArgs]);
            this.state.modal = { kind: "store", data };
        } catch (e) {
            this.state.modal = null;
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
        this.state.modalLoading = false;
    }

    async openSession(sessionId) {
        this.state.modalLoading = true;
        this.state.modal = { kind: "session", data: null };
        try {
            const data = await this.orm.call(
                "feliza.dashboard", "get_session_detail", [sessionId]);
            this.state.modal = { kind: "session", data };
        } catch (e) {
            this.state.modal = null;
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
        this.state.modalLoading = false;
    }

    async openStoreOrders(store) {
        try {
            const act = await this.orm.call("feliza.dashboard", "open_view",
                ["store_orders", store, ...this.periodArgs, store]);
            await this.action.doAction(act);
        } catch (e) {
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
    }

    get modalMaxHour() {
        const d = this.state.modal && this.state.modal.data;
        const h = (d && d.hourly) || [];
        return Math.max(1, ...h.map((x) => x.revenue || 0));
    }
    get modalMaxProduct() {
        const d = this.state.modal && this.state.modal.data;
        const t = (d && d.top_products) || [];
        return Math.max(1, ...t.map((x) => x.qty || 0));
    }

    closeModal() {
        this.state.modal = null;
    }

    async openOrderInOdoo(orderId) {
        try {
            const act = await this.orm.call("feliza.dashboard", "open_view",
                ["order_form", orderId, ...this.periodArgs, this.state.store]);
            await this.action.doAction(act);
        } catch (e) {
            this.notification.add((e && e.message && e.message.data
                && e.message.data.message) || String(e), { type: "warning" });
        }
    }

    // ------------------------------------------------------------------ //
    //  Mini grafiklar (SVG)                                               //
    // ------------------------------------------------------------------ //
    _points(values, w, h, pad = 2) {
        const n = values.length;
        if (!n) return [];
        const max = Math.max(...values);
        const min = Math.min(...values, 0);
        const span = (max - min) || 1;
        const step = n > 1 ? (w - pad * 2) / (n - 1) : 0;
        return values.map((v, i) => [
            pad + i * step,
            h - pad - ((v - min) / span) * (h - pad * 2),
        ]);
    }

    /** Kichik trend chizig'i — KPI kartochkalari uchun */
    spark(key, w = 130, h = 30) {
        const tr = (this.state.overview && this.state.overview.trend) || [];
        if (tr.length < 2) return "";
        const pts = this._points(tr.map((d) => Number(d[key]) || 0), w, h);
        return pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
    }

    /** Soatlik to'planma tushum — asosiy grafik */
    _cumulative(rows) {
        let acc = 0;
        return (rows || []).map((r) => (acc += Number(r.revenue) || 0));
    }

    get chartW() { return 640; }
    get chartH() { return 170; }

    get chartMax() {
        const a = this._cumulative(this.state.overview && this.state.overview.hourly);
        const b = this._cumulative(this.state.overview && this.state.overview.hourly_prev);
        return Math.max(1, ...a, ...b);
    }

    _chartPath(rows) {
        const vals = this._cumulative(rows);
        if (!vals.length) return "";
        const max = this.chartMax;
        const w = this.chartW, h = this.chartH;
        const step = (w - 4) / (vals.length - 1 || 1);
        return vals.map((v, i) => (i ? "L" : "M")
            + (2 + i * step).toFixed(1) + ","
            + (h - 4 - (v / max) * (h - 12)).toFixed(1)).join(" ");
    }

    get chartToday() {
        return this._chartPath(this.state.overview && this.state.overview.hourly);
    }
    get chartPrev() {
        return this._chartPath(this.state.overview && this.state.overview.hourly_prev);
    }
    get chartArea() {
        const p = this.chartToday;
        if (!p) return "";
        return p + " L" + (this.chartW - 2) + "," + (this.chartH - 4)
                 + " L2," + (this.chartH - 4) + " Z";
    }
    get chartHasData() {
        const rows = (this.state.overview && this.state.overview.hourly) || [];
        return rows.some((r) => r.revenue > 0);
    }

    // ---------- asosiy grafik: crosshair + tooltip ---------- //

    get hourRows() {
        return (this.state.overview && this.state.overview.hourly) || [];
    }
    get cumCur() { return this._cumulative(this.hourRows); }
    get cumPrev() {
        return this._cumulative(this.state.overview && this.state.overview.hourly_prev);
    }

    /** i-nuqtaning viewBox ichidagi X koordinatasi */
    chartX(i) {
        const n = this.cumCur.length;
        const step = (this.chartW - 4) / ((n - 1) || 1);
        return (2 + i * step).toFixed(1);
    }
    /** qiymatning viewBox ichidagi Y koordinatasi */
    chartYv(v) {
        if (v === null || v === undefined) return null;
        return (this.chartH - 4 - (v / this.chartMax) * (this.chartH - 12)).toFixed(1);
    }
    get tipY1() { return this.chartYv(this.cumCur[this.state.tip.i]); }
    get tipY2() {
        const p = this.cumPrev;
        return p.length > this.state.tip.i ? this.chartYv(p[this.state.tip.i]) : null;
    }

    /**
     * Sichqoncha 2px chiziqqa emas, SOATGA qaratiladi: eng yaqin nuqtaga
     * "yopishadi". Shuning uchun butun SVG ustida pointermove tinglanadi.
     */
    onChartMove(ev) {
        const cur = this.cumCur;
        const n = cur.length;
        if (n < 2) return;
        const r = ev.currentTarget.getBoundingClientRect();
        if (!r.width) return;
        const rel = (ev.clientX - r.left) / r.width;
        const i = Math.max(0, Math.min(n - 1, Math.round(rel * (n - 1))));

        const prev = this.cumPrev;
        const vCur = cur[i];
        const vPrev = prev.length > i ? prev[i] : null;
        const rows = [
            { label: "Joriy davr", value: this.money(vCur), cls: "c1" },
        ];
        if (vPrev !== null) {
            rows.push({ label: "Oldingi davr", value: this.money(vPrev), cls: "c2" });
            const d = vCur - vPrev;
            rows.push({
                label: "Farq",
                value: (d >= 0 ? "+" : "−") + this.money(Math.abs(d)),
                cls: d >= 0 ? "up" : "dn",
            });
        }
        const hour = this.hourRows[i] && this.hourRows[i].hour;
        const title = (hour === undefined ? "" : hour + ":00") + " holatiga to'plangan";
        if (this._sameTip(this.state.tip, title, rows, i)) {
            this._moveTipEl(ev);     // o'sha soat ichida — render yo'q
            return;
        }
        const p = this._tipPos(ev);
        this.state.tip = { x: p.x, y: p.y, i, title, rows };
    }

    // ------------------------------------------------------------------ //
    //  Ombor — do'kon bo'yicha qoldiq                                     //
    // ------------------------------------------------------------------ //
    async loadStockDetail() {
        this.state.stockBusy = true;
        try {
            this.state.stockDetail = await this.orm.call(
                "feliza.dashboard", "get_stock_detail",
                [this.state.stockWh, this.state.stockQuery, DETAIL_LIMIT,
                 this.state.stockOrder]);
        } catch (e) {
            this.state.error = (e && e.message && e.message.data
                && e.message.data.message) || String(e);
        }
        this.state.stockBusy = false;
    }

    async openWarehouse(row) {
        if (this.state.stockWh === row.id) {
            this.state.stockWh = null;
            this.state.stockWhName = "";
            this.state.stockDetail = null;
            return;
        }
        this.state.stockWh = row.id;
        this.state.stockWhName = row.name;
        this.state.stockQuery = "";
        this.pgReset("stock");
        await this.loadStockDetail();
    }

    onStockQuery(ev) {
        this.state.stockQuery = ev.target.value || "";
        this.pgReset("stock");   // yangi qidiruv — 1-sahifadan
        clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => this.loadStockDetail(), 400);
    }

    async setStockOrder(ev) {
        this.state.stockOrder = ev.target.value || "value";
        this.pgReset("stock");
        await this.loadStockDetail();
    }

    // ------------------------------------------------------------------ //
    get maxStoreDiscount() {
        const rows = (this.state.discounts && this.state.discounts.stores) || [];
        return Math.max(1, ...rows.map((r) => r.discount || 0));
    }
    get maxProductDiscount() {
        const rows = (this.state.discounts && this.state.discounts.products) || [];
        return Math.max(1, ...rows.map((r) => r.discount || 0));
    }
    get maxBucket() {
        const rows = (this.state.discounts && this.state.discounts.buckets) || [];
        return Math.max(1, ...rows.map((r) => r.discount || 0));
    }
    get maxAccount() {
        const rows = (this.state.finance && this.state.finance.accounts) || [];
        return Math.max(1, ...rows.map((r) => Math.abs(r.balance || 0)));
    }
    get maxFlowQty() {
        const rows = (this.state.transfers && this.state.transfers.flows) || [];
        return Math.max(1, ...rows.map((r) => r.qty || 0));
    }
    get maxWhMove() {
        const rows = (this.state.transfers && this.state.transfers.warehouses) || [];
        return Math.max(1, ...rows.map((r) => Math.max(r.sent || 0, r.received || 0)));
    }
    get maxKamShop() {
        const rows = (this.state.kamomat && this.state.kamomat.shops) || [];
        return Math.max(1, ...rows.map((r) => r.qty || 0));
    }
    get maxKamProduct() {
        const rows = (this.state.kamomat && this.state.kamomat.products) || [];
        return Math.max(1, ...rows.map((r) => r.qty || 0));
    }
    get maxWhUnits() {
        const rows = (this.state.stockStores && this.state.stockStores.rows) || [];
        return Math.max(1, ...rows.map((r) => r.units || 0));
    }

    // ------------------------------------------------------------------ //
    get maxStoreRevenue() {
        const rows = (this.state.overview && this.state.overview.stores) || [];
        return Math.max(1, ...rows.map((r) => r.revenue || 0));
    }
    get maxHourly() {
        const h = (this.state.overview && this.state.overview.hourly) || [];
        return Math.max(1, ...h.map((x) => x.revenue || 0));
    }
    get activeHours() {
        const h = (this.state.overview && this.state.overview.hourly) || [];
        return h.filter((x) => x.revenue > 0);
    }
    /** kunlik jami — soatlik ulushni hisoblash uchun */
    get totalHourly() {
        const h = (this.state.overview && this.state.overview.hourly) || [];
        return h.reduce((a, x) => a + (x.revenue || 0), 0);
    }
    get maxTopQty() {
        const t = (this.state.overview && this.state.overview.top_products) || [];
        return Math.max(1, ...t.map((x) => x.qty || 0));
    }
}

registry.category("actions").add("feliza_dashboard", FelizaDashboard);
