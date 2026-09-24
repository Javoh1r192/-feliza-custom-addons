# -*- coding: utf-8 -*-
"""
FELIZA DASHBOARD — ma'lumot qatlami
===================================

XAVFSIZLIK TAMOYILI
-------------------
Tannarx / marja / foyda faqat "Dashboard: Rahbar" guruhi uchun
HISOBLANADI. Do'kon boshlig'i uchun bu qiymatlar umuman hisoblanmaydi
va javob lug'atiga QO'SHILMAYDI — ya'ni brauzerga yuborilmaydi.

Bu muhim: agar ma'lumotni yuborib, faqat ekranda yashirsak, uni F12
(developer tools) orqali ko'rish mumkin bo'lardi. Shuning uchun
ajratish shu yerda — Python darajasida.

Xuddi shunday do'kon filtri ham: foydalanuvchi qaysi kassalarni
ko'rishi _allowed_configs() da serverda aniqlanadi. Frontend'dan
kelgan store parametri faqat SHU ro'yxat ichida filtrlay oladi —
tashqarisiga chiqa olmaydi.
"""
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

GROUP_MANAGER = "feliza_dashboard.group_feliza_dashboard_manager"
GROUP_STORE = "feliza_dashboard.group_feliza_dashboard_store"
GROUP_STOCK = "feliza_dashboard.group_feliza_dashboard_stock"
GROUP_PURCHASE = "feliza_dashboard.group_feliza_dashboard_purchase"

POS_DONE_STATES = ("paid", "done", "invoiced")


class FelizaDashboard(models.AbstractModel):
    _name = "feliza.dashboard"
    _description = "Feliza Dashboard — ma'lumot manbai"

    # ================================================================== #
    #  HUQUQ VA QAMROV                                                    #
    # ================================================================== #
    @api.model
    def _is_manager(self):
        return self.env.user.has_group(GROUP_MANAGER)

    @api.model
    def _is_store_user(self):
        return self.env.user.has_group(GROUP_STORE)

    @api.model
    def _is_stock_user(self):
        """Ombor xodimi — faqat qoldiq va o'tkazmalarni ko'radi."""
        return self.env.user.has_group(GROUP_STOCK)

    @api.model
    def _check_access_dashboard(self):
        if not (self._is_manager() or self._is_store_user()
                or self._is_stock_user()
                or self.env.user.has_group(GROUP_PURCHASE)):
            raise AccessError(_("Sizda Dashboard'ni ko'rish huquqi yo'q."))

    @api.model
    def _check_sales_access(self):
        """Sotuv bo'limlari — ombor xodimiga yopiq."""
        self._check_access_dashboard()
        if not (self._is_manager() or self._is_store_user()):
            raise AccessError(_("Sotuv ma'lumotlari sizga ochiq emas."))

    @api.model
    def _show_cost(self):
        """Tannarx/marja ko'rsatilsinmi. FAQAT rahbar uchun True."""
        return self._is_manager()

    @api.model
    def _allowed_configs(self):
        """Foydalanuvchi ko'ra oladigan pos.config yozuvlari.

        Rahbar    → kompaniyadagi barcha kassalar
        Do'kon b. → faqat unga biriktirilgan kassalar
        """
        self._check_access_dashboard()
        Config = self.env["pos.config"].sudo()

        if not (self._is_manager() or self._is_store_user()):
            return Config.browse()          # ombor xodimi — sotuv yo'q

        if self._is_manager():
            return Config.search([("company_id", "in", self.env.companies.ids)])

        configs = self.env.user.sudo().feliza_dashboard_config_ids
        # xavfsizlik: kompaniya bo'yicha ham cheklaymiz
        return configs.filtered(lambda c: c.company_id.id in self.env.companies.ids)

    @api.model
    def _scoped_configs(self, store=None):
        """Ruxsat etilgan kassalar, kerak bo'lsa do'kon bo'yicha filtrlangan.

        MUHIM: store parametri faqat ruxsat etilgan ro'yxat ICHIDA
        filtrlaydi. Boshqa do'kon nomini yuborsa — bo'sh natija qaytadi.
        """
        configs = self._allowed_configs()
        if store:
            configs = configs.filtered(
                lambda c: ((c.feliza_store_group or "").strip() or c.name) == store)
        return configs

    # ================================================================== #
    #  SANA YORDAMCHILARI                                                 #
    # ================================================================== #
    @api.model
    def _tz(self):
        return pytz.timezone(self.env.user.tz or "Asia/Tashkent")

    @api.model
    def _today(self):
        return datetime.now(self._tz()).date()

    @api.model
    def _to_utc(self, local_dt):
        return self._tz().localize(local_dt).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.model
    def _period_dates(self, period, date_from=None, date_to=None):
        today = self._today()
        if period == "custom" and date_from and date_to:
            return fields.Date.to_date(date_from), fields.Date.to_date(date_to)
        if period == "today":
            return today, today
        if period == "yesterday":
            d = today - timedelta(days=1)
            return d, d
        if period == "week":
            return today - timedelta(days=today.weekday()), today
        if period == "month":
            return today.replace(day=1), today
        if period == "quarter":
            return today.replace(month=3 * ((today.month - 1) // 3) + 1, day=1), today
        if period == "year":
            return today.replace(month=1, day=1), today
        return today, today

    @api.model
    def _bounds(self, date_from, date_to):
        """Mahalliy sanalarni UTC datetime chegaralariga aylantiradi."""
        return (
            self._to_utc(datetime.combine(date_from, time.min)),
            self._to_utc(datetime.combine(date_to, time.max)),
        )

    @api.model
    def _prev_period(self, date_from, date_to):
        """Taqqoslash uchun oldingi davr (bir xil uzunlikda)."""
        span = (date_to - date_from).days + 1
        return date_from - timedelta(days=span), date_to - timedelta(days=span)

    @api.model
    def _lfl_period(self, date_from, date_to):
        """O'tgan yilning shu davri (LFL taqqoslash uchun)."""
        try:
            return (date_from.replace(year=date_from.year - 1),
                    date_to.replace(year=date_to.year - 1))
        except ValueError:  # 29-fevral
            return (date_from - timedelta(days=365), date_to - timedelta(days=365))

    # ================================================================== #
    #  ASOSIY SO'ROV                                                      #
    # ================================================================== #
    @api.model
    def _order_domain(self, configs, date_from, date_to):
        dt_from, dt_to = self._bounds(date_from, date_to)
        return [
            ("config_id", "in", configs.ids),
            ("state", "in", list(POS_DONE_STATES)),
            ("date_order", ">=", dt_from),
            ("date_order", "<=", dt_to),
        ]

    @api.model
    def _totals(self, configs, date_from, date_to):
        """Davr bo'yicha asosiy ko'rsatkichlar.

        Qaytaradi: revenue, orders, units, discount, returns, cost*
        (* cost faqat rahbar uchun)
        """
        if not configs:
            return {"revenue": 0.0, "orders": 0, "units": 0.0,
                    "discount": 0.0, "returns": 0.0, "return_orders": 0}

        Order = self.env["pos.order"].sudo()
        orders = Order.search(self._order_domain(configs, date_from, date_to))

        revenue = 0.0
        returns = 0.0
        return_orders = 0
        units = 0.0
        discount_amount = 0.0
        cost = 0.0
        show_cost = self._show_cost()
        has_discount = self.env["feliza.detect"].has_discount()

        for order in orders:
            total = order.amount_total
            revenue += total
            if total < 0:
                returns += abs(total)
                return_orders += 1

            for line in order.lines:
                qty = line.qty or 0.0
                units += qty
                if has_discount and line.discount:
                    # chegirmasiz summa - chegirmali summa
                    gross = (line.price_unit or 0.0) * qty
                    discount_amount += gross * (line.discount / 100.0)
                if show_cost:
                    # ORM orqali o'qiymiz — standard_price Odoo 19 da
                    # jsonb bo'lsa ham ORM float qaytaradi
                    cost += (line.product_id.standard_price or 0.0) * qty

        result = {
            "revenue": revenue,
            "orders": len(orders),
            "units": units,
            "discount": discount_amount,
            "returns": returns,
            "return_orders": return_orders,
        }
        if show_cost:
            result["cost"] = cost
            result["margin"] = (revenue - cost) / revenue * 100.0 if revenue else 0.0
            result["profit"] = revenue - cost
        return result

    @api.model
    def _kpis(self, totals):
        rev = totals.get("revenue") or 0.0
        cnt = totals.get("orders") or 0
        return {
            "revenue": rev,
            "orders": cnt,
            "avg_check": rev / cnt if cnt else 0.0,
            "upt": (totals.get("units") or 0.0) / cnt if cnt else 0.0,
            "discount_pct": (totals.get("discount") or 0.0) / rev * 100.0 if rev else 0.0,
            "return_pct": (totals.get("returns") or 0.0) / rev * 100.0 if rev else 0.0,
        }

    # ================================================================== #
    #  KONFIGURATSIYA (frontend uchun)                                    #
    # ================================================================== #
    @api.model
    def get_config(self):
        self._check_access_dashboard()
        configs = self._allowed_configs()
        store_map = self.env["pos.config"]._feliza_store_map(configs)
        company = self.env.company

        is_manager = self._is_manager()
        is_store = self._is_store_user()
        is_stock = self._is_stock_user()
        is_purchase = self._is_purchase_user()
        zakup_tabs = ["zakup", "zsales", "zstock", "zincome"]
        if is_manager:
            tabs = ["today", "stores", "sales", "staff", "products", "disc",
                    "stock", "transfer", "kam"] + zakup_tabs + ["fin", "diag"]
        elif is_store:
            tabs = ["today", "stores", "sales", "staff", "products", "disc",
                    "stock", "transfer", "kam"]
            if is_purchase:
                tabs += zakup_tabs
        elif is_stock:
            tabs = ["stock", "transfer", "kam"]
            if is_purchase:
                tabs += zakup_tabs
        else:
            tabs = zakup_tabs

        # Modulning eski versiyasida kamomat maydonlari yo'q — bo'limni
        # umuman ko'rsatmaymiz (bo'sh oyna chiqmasin).
        if not self.env["feliza.detect"].has_kamomat():
            tabs = [t for t in tabs if t != "kam"]

        return {
            "is_manager": is_manager,
            "is_store": is_store,
            "is_stock": is_stock,
            "is_purchase": is_purchase,
            "tabs": tabs,
            "default_tab": tabs[0],
            "show_cost": self._show_cost(),
            "stores": sorted(store_map.keys()),
            "store_count": len(store_map),
            "user_name": self.env.user.name,
            "company_name": company.name,
            "currency": {
                "symbol": company.currency_id.symbol,
                "position": company.currency_id.position,
            },
            "detect": self.env["feliza.detect"]._detect(),
            "has_targets": bool(
                self.env["feliza.sales.target"].sudo().search_count([])),
            # Rahbar zakupchi statistikasida xodim tanlay oladi
            "zakupchi_list": self._zakupchi_list() if is_manager else [],
        }

    @api.model
    def _zakupchi_list(self):
        """Zakup qilgan yoki tovar yaratgan foydalanuvchilar."""
        cr = self.env.cr
        cr.execute("""
            SELECT DISTINCT u.id, p.name
              FROM res_users u
              JOIN res_partner p ON p.id = u.partner_id
             WHERE u.active AND NOT u.share
               AND (EXISTS (SELECT 1 FROM purchase_order po
                             WHERE po.user_id = u.id OR po.create_uid = u.id)
                 OR EXISTS (SELECT 1 FROM product_template pt
                             WHERE pt.create_uid = u.id))
             ORDER BY p.name
        """)
        return [{"id": i, "name": n} for i, n in cr.fetchall()]

    # ================================================================== #
    #  1 · UMUMIY KO'RINISH                                               #
    # ================================================================== #
    @api.model
    def get_overview(self, period="today", date_from=None, date_to=None, store=None):
        self._check_sales_access()
        configs = self._scoped_configs(store)
        d_from, d_to = self._period_dates(period, date_from, date_to)

        totals = self._totals(configs, d_from, d_to)
        kpi = self._kpis(totals)

        # taqqoslash — oldingi davr
        p_from, p_to = self._prev_period(d_from, d_to)
        prev = self._kpis(self._totals(configs, p_from, p_to))

        # reja
        target = self.env["feliza.sales.target"].get_period_target(
            configs.ids, d_from, d_to)

        data = {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "kpi": kpi,
            "prev": prev,
            "delta": {
                k: self._pct_delta(kpi.get(k), prev.get(k))
                for k in ("revenue", "orders", "avg_check", "upt")
            },
            "target": target,
            "target_pct": (kpi["revenue"] / target * 100.0) if target else None,
            "stores": self._store_rows(configs, d_from, d_to),
            "hourly": self._hourly(configs, d_from, d_to),
            "hourly_prev": self._hourly(configs, p_from, p_to),
            "trend": self._trend(configs, days=14),
            "top_products": self._top_products(configs, d_from, d_to, limit=8),
            "payments": self._payments(configs, d_from, d_to),
            "alerts": self._alerts(configs, d_from, d_to),
        }
        if self._show_cost():
            data["margin"] = totals.get("margin", 0.0)
            data["profit"] = totals.get("profit", 0.0)
        return data

    @api.model
    def _pct_delta(self, now, before):
        if not before:
            return None
        return (now - before) / before * 100.0

    # ================================================================== #
    #  DO'KONLAR KESIMI                                                   #
    # ================================================================== #
    @api.model
    def _store_rows(self, configs, date_from, date_to):
        """Har bir do'kon bo'yicha qator."""
        store_map = self.env["pos.config"]._feliza_store_map(configs)
        Target = self.env["feliza.sales.target"]
        Config = self.env["pos.config"].sudo()
        show_cost = self._show_cost()

        lfl_from, lfl_to = self._lfl_period(date_from, date_to)
        rows = []

        for store_name, cfg_ids in store_map.items():
            cfgs = Config.browse(cfg_ids)
            totals = self._totals(cfgs, date_from, date_to)
            kpi = self._kpis(totals)
            target = Target.get_period_target(cfg_ids, date_from, date_to)
            lfl_kpi = self._kpis(self._totals(cfgs, lfl_from, lfl_to))

            row = {
                "store": store_name,
                "config_ids": cfg_ids,
                "revenue": kpi["revenue"],
                "orders": kpi["orders"],
                "avg_check": kpi["avg_check"],
                "upt": kpi["upt"],
                "discount_pct": kpi["discount_pct"],
                "return_pct": kpi["return_pct"],
                "target": target,
                "target_pct": (kpi["revenue"] / target * 100.0) if target else None,
                "lfl": self._pct_delta(kpi["revenue"], lfl_kpi["revenue"]),
            }
            if show_cost:
                row["margin"] = totals.get("margin", 0.0)
                row["profit"] = totals.get("profit", 0.0)
            rows.append(row)

        rows.sort(key=lambda r: r["revenue"], reverse=True)
        return rows

    # ================================================================== #
    #  SOATLIK DINAMIKA                                                   #
    # ================================================================== #
    @api.model
    def _hourly(self, configs, date_from, date_to):
        """Soat bo'yicha tushum (mahalliy vaqtda)."""
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)
        tz_name = self.env.user.tz or "Asia/Tashkent"

        self.env.cr.execute("""
            SELECT EXTRACT(HOUR FROM (date_order AT TIME ZONE 'UTC'
                                                 AT TIME ZONE %s))::int AS h,
                   SUM(amount_total) AS total,
                   COUNT(*) AS cnt
              FROM pos_order
             WHERE config_id = ANY(%s)
               AND state = ANY(%s)
               AND date_order >= %s AND date_order <= %s
             GROUP BY 1 ORDER BY 1
        """, (tz_name, configs.ids, list(POS_DONE_STATES), dt_from, dt_to))

        found = {r[0]: {"revenue": float(r[1] or 0), "orders": r[2]}
                 for r in self.env.cr.fetchall()}
        return [{"hour": h,
                 "revenue": found.get(h, {}).get("revenue", 0.0),
                 "orders": found.get(h, {}).get("orders", 0)}
                for h in range(24)]

    # ================================================================== #
    #  MAHSULOT                                                           #
    # ================================================================== #
    @api.model
    def _top_products(self, configs, date_from, date_to, limit=10):
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)

        self.env.cr.execute("""
            SELECT l.product_id, SUM(l.qty) AS qty, SUM(l.price_subtotal_incl) AS amount
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
             GROUP BY l.product_id
             HAVING SUM(l.qty) > 0
             ORDER BY qty DESC
             LIMIT %s
        """, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to, limit))

        rows = self.env.cr.fetchall()
        products = self.env["product.product"].sudo().browse([r[0] for r in rows])
        by_id = {p.id: p for p in products}
        return [{
            "id": r[0],
            "name": by_id[r[0]].display_name if r[0] in by_id else "?",
            "qty": float(r[1] or 0),
            "amount": float(r[2] or 0),
        } for r in rows]

    # ================================================================== #
    #  TO'LOV TURLARI                                                     #
    # ================================================================== #
    @api.model
    def _payments(self, configs, date_from, date_to):
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)

        self.env.cr.execute("""
            SELECT p.payment_method_id, SUM(p.amount) AS total
              FROM pos_payment p
              JOIN pos_order o ON o.id = p.pos_order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
             GROUP BY 1 ORDER BY total DESC
        """, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))

        rows = self.env.cr.fetchall()
        total = sum(float(r[1] or 0) for r in rows) or 1.0
        methods = self.env["pos.payment.method"].sudo().browse([r[0] for r in rows])
        by_id = {m.id: m for m in methods}

        # MUHIM: har bir do'konda alohida "Наличные", "HUMO" yozuvi bor.
        # Panelda ular BITTA qator bo'lib chiqishi kerak — nomi bo'yicha
        # birlashtiramiz. Tafsilotda do'kon bo'yicha ochib beriladi.
        merged = {}
        for r in rows:
            m = by_id.get(r[0])
            name = (m.name if m else "?") or "?"
            key = name.strip().lower()
            slot = merged.setdefault(key, {
                "key": key,
                "name": name.strip(),
                "ids": [],
                "amount": 0.0,
                "is_cash": False,
            })
            slot["ids"].append(r[0])
            slot["amount"] += float(r[1] or 0)
            if m and getattr(m, "is_cash_count", False):
                slot["is_cash"] = True

        out = []
        for slot in merged.values():
            slot["pct"] = slot["amount"] / total * 100.0
            slot["methods"] = len(slot["ids"])
            out.append(slot)
        out.sort(key=lambda x: x["amount"], reverse=True)
        return out

    # ================================================================== #
    #  OGOHLANTIRISHLAR                                                   #
    # ================================================================== #
    @api.model
    def _alerts(self, configs, date_from, date_to):
        """Avtomatik aniqlanadigan muammolar."""
        alerts = []
        Target = self.env["feliza.sales.target"]
        Config = self.env["pos.config"].sudo()
        store_map = Config._feliza_store_map(configs)

        # 1) rejadan sezilarli orqada qolgan do'konlar
        for store_name, cfg_ids in store_map.items():
            target = Target.get_period_target(cfg_ids, date_from, date_to)
            if not target:
                continue
            rev = self._totals(Config.browse(cfg_ids), date_from, date_to)["revenue"]
            pct = rev / target * 100.0
            if pct < 75:
                alerts.append({
                    "level": "crit" if pct < 60 else "serious",
                    "title": _("%s — rejadan %d%% orqada") % (store_name, 100 - pct),
                    "detail": _("Reja %s, bajarilgan %s") % (
                        self._fmt(target), self._fmt(rev)),
                })

        # 2) kassa farqlari
        diff_field = self.env["feliza.detect"].cash_diff_field()
        if diff_field:
            dt_from, dt_to = self._bounds(date_from, date_to)
            sessions = self.env["pos.session"].sudo().search([
                ("config_id", "in", configs.ids),
                ("state", "=", "closed"),
                ("stop_at", ">=", dt_from), ("stop_at", "<=", dt_to),
            ])
            for s in sessions:
                diff = getattr(s, diff_field, 0.0) or 0.0
                if abs(diff) > 50000:  # 50 ming so'mdan katta farq
                    alerts.append({
                        "level": "crit" if abs(diff) > 200000 else "serious",
                        "title": _("Kassa farqi — %s") % s.config_id.name,
                        "detail": _("%s · smena %s") % (self._fmt(diff), s.name),
                    })

        # 3) me'yordan yuqori chegirma
        if self.env["feliza.detect"].has_discount():
            for store_name, cfg_ids in store_map.items():
                t = self._totals(Config.browse(cfg_ids), date_from, date_to)
                rev = t["revenue"]
                if rev <= 0:
                    continue
                pct = t["discount"] / rev * 100.0
                if pct > 15:
                    alerts.append({
                        "level": "serious",
                        "title": _("Chegirma me'yordan yuqori — %s") % store_name,
                        "detail": _("%.1f%% (odatda 10%% dan past)") % pct,
                    })

        order = {"crit": 0, "serious": 1, "warn": 2}
        alerts.sort(key=lambda a: order.get(a["level"], 3))
        return alerts[:10]

    @api.model
    def _fmt(self, value):
        """Summani qisqa ko'rinishda."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return str(value)
        if abs(v) >= 1e9:
            return "%.2f mlrd" % (v / 1e9)
        if abs(v) >= 1e6:
            return "%.1f mln" % (v / 1e6)
        if abs(v) >= 1e3:
            return "%.0f ming" % (v / 1e3)
        return "%.0f" % v

    # ================================================================== #
    #  2 · XODIMLAR                                                       #
    # ================================================================== #
    @api.model
    def get_staff(self, period="month", date_from=None, date_to=None, store=None):
        self._check_sales_access()
        configs = self._scoped_configs(store)
        d_from, d_to = self._period_dates(period, date_from, date_to)

        return {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "salespeople": self._salespeople(configs, d_from, d_to),
            "cashiers": self._cashiers(configs, d_from, d_to),
            "hourly": self._hourly(configs, d_from, d_to),
            "coverage": self._salesperson_coverage(configs, d_from, d_to),
            "detect": {
                "salesperson": self.env["feliza.detect"].salesperson_info(),
                "cashier": self.env["feliza.detect"].cashier_info(),
            },
        }

    @api.model
    def _salesperson_coverage(self, configs, date_from, date_to):
        """Nechta chekda sotuvchi ko'rsatilmagan.

        Reyting faqat sotuvchisi yozilgan cheklar bo'yicha tuziladi.
        Agar bir qism cheklar bo'sh bo'lsa — reyting to'liq emas, buni
        yashirmasdan aytish kerak, aks holda rahbar noto'g'ri xulosa qiladi.
        """
        info = self.env["feliza.detect"].salesperson_info()
        if not info or not configs or info.get("is_fallback"):
            return None
        dt_from, dt_to = self._bounds(date_from, date_to)
        field, on_line = info["field"], info.get("on_line")

        if on_line:
            sql = """
                SELECT COUNT(DISTINCT o.id),
                       COUNT(DISTINCT o.id) FILTER (
                           WHERE NOT EXISTS (SELECT 1 FROM pos_order_line l
                                              WHERE l.order_id = o.id
                                                AND l.{f} IS NOT NULL)),
                       COALESCE(SUM(o.amount_total) FILTER (
                           WHERE NOT EXISTS (SELECT 1 FROM pos_order_line l
                                              WHERE l.order_id = o.id
                                                AND l.{f} IS NOT NULL)), 0)
                  FROM pos_order o
                 WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
                   AND o.date_order >= %s AND o.date_order <= %s
            """.format(f=field)
        else:
            sql = """
                SELECT COUNT(*),
                       COUNT(*) FILTER (WHERE o.{f} IS NULL),
                       COALESCE(SUM(o.amount_total) FILTER (
                           WHERE o.{f} IS NULL), 0)
                  FROM pos_order o
                 WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
                   AND o.date_order >= %s AND o.date_order <= %s
            """.format(f=field)
        try:
            self.env.cr.execute(
                sql, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))
            total, empty, empty_amount = self.env.cr.fetchone()
        except Exception:
            return None
        total = int(total or 0)
        empty = int(empty or 0)
        return {
            "orders": total,
            "empty": empty,
            "empty_amount": float(empty_amount or 0),
            "pct": (100.0 * (total - empty) / total) if total else 0.0,
        }

    @api.model
    def _salespeople(self, configs, date_from, date_to):
        """Sotuvchilar reytingi — aniqlangan maydon asosida."""
        info = self.env["feliza.detect"].salesperson_info()
        if not info or not configs:
            return []

        dt_from, dt_to = self._bounds(date_from, date_to)
        field = info["field"]

        if info["on_line"]:
            # sotuvchi qator darajasida
            query = """
                SELECT l.{field} AS sp, SUM(l.price_subtotal_incl) AS amount,
                       COUNT(DISTINCT o.id) AS orders, SUM(l.qty) AS units
                  FROM pos_order_line l
                  JOIN pos_order o ON o.id = l.order_id
                 WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
                   AND o.date_order >= %s AND o.date_order <= %s
                   AND l.{field} IS NOT NULL
                 GROUP BY 1 ORDER BY amount DESC LIMIT 500
            """.format(field=field)
        else:
            query = """
                SELECT o.{field} AS sp, SUM(o.amount_total) AS amount,
                       COUNT(*) AS orders,
                       COALESCE(SUM((SELECT SUM(l.qty) FROM pos_order_line l
                                      WHERE l.order_id = o.id)), 0) AS units
                  FROM pos_order o
                 WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
                   AND o.date_order >= %s AND o.date_order <= %s
                   AND o.{field} IS NOT NULL
                 GROUP BY 1 ORDER BY amount DESC LIMIT 500
            """.format(field=field)

        try:
            self.env.cr.execute(
                query, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))
            rows = self.env.cr.fetchall()
        except Exception:
            return []

        recs = self.env[info["comodel"]].sudo().browse([r[0] for r in rows])
        by_id = {r.id: r for r in recs}

        result = []
        for r in rows:
            orders = r[2] or 0
            amount = float(r[1] or 0)
            units = float(r[3] or 0)
            result.append({
                "id": r[0],
                "model": info["comodel"],
                "name": by_id[r[0]].display_name if r[0] in by_id else "?",
                "revenue": amount,
                "orders": orders,
                "avg_check": amount / orders if orders else 0.0,
                "upt": units / orders if orders else 0.0,
            })
        return result

    @api.model
    def _cashiers(self, configs, date_from, date_to):
        """Kassirlar — chek soni, tushum va kassa aniqligi.

        Kassir — Odoo'ning O'Z maydoni (`pos.order.employee_id`, yorlig'i
        «Cashier»). Sotuvchi bu emas: sotuvchi alohida custom maydonda,
        yuqoridagi `_salespeople` o'sha yerdan o'qiydi.

        Ilgari bu jadval faqat YOPILGAN sessiyalardan tuzilardi — davr
        ichida bironta smena yopilmagan bo'lsa (masalan «Bugun»), jadval
        butunlay bo'sh chiqardi. Endi asos — cheklar; kassa farqi esa
        ustiga qo'shiladi.
        """
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)
        info = self.env["feliza.detect"].cashier_info()

        rows = []
        if info and not info.get("on_line"):
            field = info["field"]
            try:
                self.env.cr.execute("""
                    SELECT o.{f}                     AS person,
                           COALESCE(SUM(o.amount_total), 0) AS revenue,
                           COUNT(*)                  AS orders,
                           COUNT(DISTINCT o.session_id) AS sessions,
                           ARRAY_AGG(DISTINCT COALESCE(
                               NULLIF(c.feliza_store_group, ''),
                               NULLIF(c.feliza_store_name, ''), c.name)) AS stores
                      FROM pos_order o
                      JOIN pos_config c ON c.id = o.config_id
                     WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
                       AND o.date_order >= %s AND o.date_order <= %s
                       AND o.{f} IS NOT NULL
                     GROUP BY 1
                """.format(f=field),
                    (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))
                rows = self.env.cr.fetchall()
            except Exception:
                rows = []

        # --- kassa farqi: yopilgan smenalar bo'yicha ---------------------
        #  «Sanalmagan» smena (kassir yopishda naqdni kiritmagan) haqiqiy
        #  kamomad emas — uni farqqa qo'shmaymiz, alohida sanaymiz.
        #
        #  DIQQAT: `cash_register_difference` — Odoo 19'da HISOBLANADIGAN
        #  maydon, bazada ustuni yo'q. Shuning uchun bu yerda SQL emas,
        #  ORM ishlatiladi (davrdagi smenalar soni oz — bu tez).
        sessions = self.env["pos.session"].sudo().search([
            ("config_id", "in", configs.ids),
            ("state", "=", "closed"),
            ("stop_at", ">=", dt_from), ("stop_at", "<=", dt_to),
        ])
        cash_sales = {}
        if sessions:
            self.env.cr.execute("""
                SELECT o.session_id, COALESCE(SUM(p.amount), 0)
                  FROM pos_payment p
                  JOIN pos_order o ON o.id = p.pos_order_id
                  JOIN pos_payment_method m ON m.id = p.payment_method_id
                 WHERE o.session_id = ANY(%s) AND o.state = ANY(%s)
                   AND m.is_cash_count IS TRUE
                 GROUP BY 1
            """, (sessions.ids, list(POS_DONE_STATES)))
            cash_sales = {r[0]: float(r[1] or 0)
                          for r in self.env.cr.fetchall()}

        by_user = {}
        for s in sessions:
            uid = s.user_id.id
            if not uid:
                continue
            cnt, diff, nc = by_user.get(uid, (0, 0.0, 0))
            not_counted = (cash_sales.get(s.id, 0.0) > 0.01
                           and abs(s.cash_register_balance_end_real or 0.0) < 0.01)
            by_user[uid] = (
                cnt + 1,
                diff + (0.0 if not_counted else (s.cash_register_difference or 0.0)),
                nc + (1 if not_counted else 0),
            )

        comodel = (info or {}).get("comodel") or "res.users"
        recs = self.env[comodel].sudo().browse([r[0] for r in rows])
        by_id = {r.id: r for r in recs.exists()}

        # kassir hr.employee bo'lsa — smena res.users'ga yozilgan, bog'laymiz
        emp_to_user = {}
        if comodel == "hr.employee" and by_id:
            for e in recs.exists():
                if e.user_id:
                    emp_to_user[e.id] = e.user_id.id

        result = []
        seen_users = set()
        for r in rows:
            pid = r[0]
            uid = emp_to_user.get(pid, pid if comodel == "res.users" else None)
            sess, diff, nc = by_user.get(uid, (0, 0.0, 0)) if uid else (0, 0.0, 0)
            if uid:
                seen_users.add(uid)
            stores = [s for s in (r[4] or []) if s]
            result.append({
                "id": pid,
                "model": comodel,
                "name": by_id[pid].display_name if pid in by_id else _("Noma'lum"),
                "store": ", ".join(stores[:2]) + ("…" if len(stores) > 2 else ""),
                "orders": int(r[2] or 0),
                "revenue": float(r[1] or 0),
                # smena soni: yopilganlari aniq bo'lsa o'shani, aks holda
                # cheklardagi turli smenalar sonini ko'rsatamiz
                "sessions": sess or int(r[3] or 0),
                "difference": diff,
                "not_counted": nc,
            })

        # cheki yo'q, lekin smena yopgan kassirlar ham ko'rinsin
        for uid, (sess, diff, nc) in by_user.items():
            if uid in seen_users or not uid:
                continue
            user = self.env["res.users"].sudo().browse(uid)
            if not user.exists():
                continue
            result.append({
                "id": uid, "model": "res.users",
                "name": user.display_name, "store": "",
                "orders": 0, "revenue": 0.0,
                "sessions": sess, "difference": diff, "not_counted": nc,
            })

        result.sort(key=lambda r: (-r["revenue"], r["difference"]))
        return result

    # ================================================================== #
    #  3 · MAHSULOT                                                       #
    # ================================================================== #
    @api.model
    def get_products(self, period="month", date_from=None, date_to=None, store=None):
        self._check_sales_access()
        configs = self._scoped_configs(store)
        d_from, d_to = self._period_dates(period, date_from, date_to)

        return {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "top": self._top_products(configs, d_from, d_to, limit=20),
            "sizes": self._size_curve(configs, d_from, d_to),
            "slow": self._slow_movers(configs, limit=15),
        }

    @api.model
    def _size_curve(self, configs, date_from, date_to):
        """O'lcham bo'yicha sotuv va qoldiq."""
        attr_id = self.env["feliza.detect"].size_attribute_id()
        if not attr_id or not configs:
            return []

        dt_from, dt_to = self._bounds(date_from, date_to)
        self.env.cr.execute("""
            SELECT v.id, v.name, SUM(l.qty) AS qty
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
              JOIN product_product p ON p.id = l.product_id
              JOIN product_variant_combination c
                   ON c.product_product_id = p.id
              JOIN product_template_attribute_value tav
                   ON tav.id = c.product_template_attribute_value_id
              JOIN product_attribute_value v
                   ON v.id = tav.product_attribute_value_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
               AND tav.attribute_id = %s
             GROUP BY v.id, v.name
             ORDER BY v.name
        """, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to, attr_id))

        rows = self.env.cr.fetchall()
        return [{"id": r[0],
                 "name": (r[1] or {}).get("en_US") if isinstance(r[1], dict) else r[1],
                 "sold": float(r[2] or 0)} for r in rows]

    @api.model
    def _slow_movers(self, configs, limit=15):
        """Uzoq vaqtdan beri sotilmagan tovar (do'kon zaxirasi bo'yicha)."""
        warehouses = configs.mapped("picking_type_id.warehouse_id")
        if not warehouses:
            return []

        locations = self.env["stock.location"].sudo().search([
            ("id", "child_of", warehouses.mapped("view_location_id").ids),
            ("usage", "=", "internal"),
        ])
        if not locations:
            return []

        quants = self.env["stock.quant"].sudo().search([
            ("location_id", "in", locations.ids),
            ("quantity", ">", 0),
        ], limit=2000)

        show_cost = self._show_cost()
        agg = defaultdict(lambda: {"qty": 0.0, "value": 0.0})
        for q in quants:
            key = q.product_id.id
            agg[key]["qty"] += q.quantity
            # do'kon boshlig'i uchun SOTUV narxida, rahbar uchun tannarxda
            unit = (q.product_id.standard_price if show_cost
                    else q.product_id.lst_price) or 0.0
            agg[key]["value"] += q.quantity * unit

        products = self.env["product.product"].sudo().browse(list(agg.keys()))
        by_id = {p.id: p for p in products}
        result = [{
            "id": pid,
            "name": by_id[pid].display_name if pid in by_id else "?",
            "qty": v["qty"],
            "value": v["value"],
            "value_basis": "cost" if show_cost else "sale",
        } for pid, v in agg.items()]
        result.sort(key=lambda r: r["value"], reverse=True)
        return result[:limit]

    # ================================================================== #
    #  4 · OMBOR                                                          #
    # ================================================================== #
    @api.model
    def get_stock(self, store=None):
        self._check_access_dashboard()
        configs = self._scoped_configs(store)
        return {
            "stockouts": self._stockouts(configs),
            "transit": self._transit(configs),
        }

    @api.model
    def _stockouts(self, configs, days=14, limit=25, min_units=3):
        """Yaxshi sotilayotgan, lekin zaxirasi tugagan tovarlar.

        min_units — davr ichida kamida shuncha dona sotilgan bo'lishi kerak.
        Aks holda ro'yxat tasodifiy (14 kunda 1 dona sotilgan) tovarlar
        bilan to'lib ketadi va ma'nosini yo'qotadi.
        """
        if not configs:
            return []
        d_to = self._today()
        d_from = d_to - timedelta(days=days)
        dt_from, dt_to = self._bounds(d_from, d_to)

        # so'nggi kunlardagi o'rtacha kunlik sotuv
        self.env.cr.execute("""
            SELECT l.product_id, SUM(l.qty) / %s AS daily, SUM(l.qty) AS sold
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
             GROUP BY l.product_id
             HAVING SUM(l.qty) >= %s
             ORDER BY daily DESC
             LIMIT 200
        """, (days, configs.ids, list(POS_DONE_STATES), dt_from, dt_to, min_units))
        fetched = self.env.cr.fetchall()
        daily = {r[0]: float(r[1] or 0) for r in fetched}
        sold_qty = {r[0]: float(r[2] or 0) for r in fetched}
        if not daily:
            return []

        warehouses = configs.mapped("picking_type_id.warehouse_id")
        locations = self.env["stock.location"].sudo().search([
            ("id", "child_of", warehouses.mapped("view_location_id").ids),
            ("usage", "=", "internal"),
        ])

        # Odoo 19: _read_group tuple qaytaradi (read_group eskirgan)
        groups = self.env["stock.quant"].sudo()._read_group(
            [("location_id", "in", locations.ids),
             ("product_id", "in", list(daily.keys()))],
            groupby=["product_id"],
            aggregates=["quantity:sum"])
        on_hand = {product.id: qty for product, qty in groups if product}

        products = self.env["product.product"].sudo().browse(list(daily.keys()))
        by_id = {p.id: p for p in products}

        rows = []
        for pid, rate in daily.items():
            qty = on_hand.get(pid, 0.0)
            days_left = qty / rate if rate else 999
            if days_left <= 3:
                product = by_id.get(pid)
                rows.append({
                    "id": pid,
                    "name": product.display_name if product else "?",
                    "on_hand": qty,
                    "sold": sold_qty.get(pid, 0.0),
                    "period_days": days,
                    "daily_rate": rate,
                    "days_left": days_left,
                    # yo'qotish har doim SOTUV narxida
                    "lost_per_day": rate * (product.lst_price if product else 0.0),
                })
        rows.sort(key=lambda r: r["lost_per_day"], reverse=True)
        return rows[:limit]

    @api.model
    def _transit(self, configs):
        """Yo'ldagi o'tkazmalar — omborlar aro modul bo'lsa."""
        if not self.env["feliza.detect"].has_interwh() or not configs:
            return []
        warehouses = configs.mapped("picking_type_id.warehouse_id")
        if not warehouses:
            return []

        pickings = self.env["stock.picking"].sudo().search([
            ("picking_type_code", "=", "incoming"),
            ("state", "not in", ("done", "cancel")),
            ("picking_type_id.warehouse_id", "in", warehouses.ids),
            ("inter_wh_delivery_id", "!=", False),
        ], limit=50)

        today = self._today()
        rows = []
        for p in pickings:
            src = p.inter_wh_delivery_id.picking_type_id.warehouse_id
            sched = fields.Date.to_date(p.scheduled_date) if p.scheduled_date else today
            rows.append({
                "name": p.name,
                "source": src.name if src else "-",
                "dest": p.picking_type_id.warehouse_id.name,
                "qty": sum(p.move_ids.mapped("product_uom_qty")),
                "days": (today - sched).days,
            })
        rows.sort(key=lambda r: r["days"], reverse=True)
        return rows

    # ================================================================== #
    #  DIAGNOSTIKA                                                        #
    # ================================================================== #
    @api.model
    def get_diagnostics(self):
        self._check_access_dashboard()
        if not self._is_manager():
            raise AccessError(_("Diagnostika faqat rahbar uchun."))
        return self.env["feliza.detect"].diagnostics()

    # ================================================================== #
    #  5 · CHEGIRMA — chegirmali sotuvlar tahlili                         #
    # ================================================================== #
    #  Chegirma summasi hamma joyda BIR XIL formula bilan hisoblanadi:
    #      chegirma = price_unit * qty * discount / 100
    #  Bu «Umumiy» bo'limidagi chegirma foizi bilan aynan mos tushadi.
    # ------------------------------------------------------------------ #
    @api.model
    def get_discounts(self, period="today", date_from=None, date_to=None,
                      store=None):
        self._check_sales_access()
        configs = self._scoped_configs(store)
        d_from, d_to = self._period_dates(period, date_from, date_to)

        data = {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "has_discount": self.env["feliza.detect"].has_discount(),
            "kpi": self._discount_kpi(configs, d_from, d_to),
            "stores": self._discount_by_store(configs, d_from, d_to),
            "products": self._discount_products(configs, d_from, d_to),
            "people": self._discount_people(configs, d_from, d_to),
            "buckets": self._discount_buckets(configs, d_from, d_to),
            "orders": self._discount_orders(configs, d_from, d_to),
        }
        return data

    @api.model
    def _discount_sql_head(self):
        """Chegirma bo'yicha umumiy SELECT bo'lagi."""
        return """
            SUM(l.price_unit * l.qty * l.discount / 100.0)          AS disc,
            SUM(l.price_subtotal_incl)                              AS net,
            SUM(l.qty) FILTER (WHERE l.discount > 0)                AS disc_qty,
            SUM(l.qty)                                              AS qty
        """

    @api.model
    def _discount_kpi(self, configs, date_from, date_to):
        empty = {"discount": 0.0, "net": 0.0, "gross": 0.0, "discount_pct": 0.0,
                 "orders": 0, "disc_orders": 0, "order_pct": 0.0,
                 "units": 0.0, "disc_units": 0.0, "unit_pct": 0.0,
                 "avg_pct": 0.0, "max_pct": 0.0, "avg_per_order": 0.0}
        if not configs:
            return empty
        dt_from, dt_to = self._bounds(date_from, date_to)

        self.env.cr.execute("""
            SELECT COALESCE(SUM(l.price_unit * l.qty * l.discount / 100.0), 0) AS disc,
                   COALESCE(SUM(l.price_subtotal_incl), 0)                     AS net,
                   COALESCE(SUM(l.qty), 0)                                     AS units,
                   COALESCE(SUM(l.qty) FILTER (WHERE l.discount > 0), 0)       AS disc_units,
                   COUNT(DISTINCT o.id)                                        AS orders,
                   COUNT(DISTINCT o.id) FILTER (WHERE l.discount > 0)          AS disc_orders,
                   COALESCE(MAX(l.discount), 0)                                AS max_pct
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
        """, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))
        r = self.env.cr.fetchone() or (0, 0, 0, 0, 0, 0, 0)

        disc = float(r[0] or 0)
        net = float(r[1] or 0)
        units = float(r[2] or 0)
        disc_units = float(r[3] or 0)
        orders = int(r[4] or 0)
        disc_orders = int(r[5] or 0)
        gross = net + disc

        return {
            "discount": disc,
            "net": net,
            "gross": gross,
            "discount_pct": disc / gross * 100.0 if gross else 0.0,
            "orders": orders,
            "disc_orders": disc_orders,
            "order_pct": disc_orders / orders * 100.0 if orders else 0.0,
            "units": units,
            "disc_units": disc_units,
            "unit_pct": disc_units / units * 100.0 if units else 0.0,
            "avg_pct": disc / gross * 100.0 if gross else 0.0,
            "max_pct": float(r[6] or 0),
            "avg_per_order": disc / disc_orders if disc_orders else 0.0,
        }

    @api.model
    def _discount_by_store(self, configs, date_from, date_to):
        """Do'kon bo'yicha chegirma."""
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)
        store_map = self.env["pos.config"]._feliza_store_map(configs)

        self.env.cr.execute("""
            SELECT o.config_id,
                   COALESCE(SUM(l.price_unit * l.qty * l.discount / 100.0), 0),
                   COALESCE(SUM(l.price_subtotal_incl), 0),
                   COUNT(DISTINCT o.id),
                   COUNT(DISTINCT o.id) FILTER (WHERE l.discount > 0)
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
             GROUP BY 1
        """, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))
        by_cfg = {r[0]: r for r in self.env.cr.fetchall()}

        rows = []
        for store_name, cfg_ids in store_map.items():
            disc = net = 0.0
            orders = disc_orders = 0
            for cid in cfg_ids:
                r = by_cfg.get(cid)
                if not r:
                    continue
                disc += float(r[1] or 0)
                net += float(r[2] or 0)
                orders += int(r[3] or 0)
                disc_orders += int(r[4] or 0)
            gross = net + disc
            rows.append({
                "store": store_name,
                "discount": disc,
                "net": net,
                "gross": gross,
                "pct": disc / gross * 100.0 if gross else 0.0,
                "orders": orders,
                "disc_orders": disc_orders,
                "order_pct": disc_orders / orders * 100.0 if orders else 0.0,
            })
        rows.sort(key=lambda x: x["discount"], reverse=True)
        return rows

    @api.model
    def _discount_products(self, configs, date_from, date_to, limit=20):
        """Eng ko'p chegirma berilgan tovarlar."""
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)

        self.env.cr.execute("""
            SELECT l.product_id,
                   SUM(l.price_unit * l.qty * l.discount / 100.0) AS disc,
                   SUM(l.price_subtotal_incl)                     AS net,
                   SUM(l.qty)                                     AS qty,
                   SUM(l.price_unit * l.qty)                      AS gross
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
               AND l.discount > 0
             GROUP BY 1
             ORDER BY disc DESC
             LIMIT %s
        """, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to, limit))
        rows = self.env.cr.fetchall()
        if not rows:
            return []

        products = self.env["product.product"].sudo().browse([r[0] for r in rows])
        by_id = {p.id: p for p in products}
        out = []
        for r in rows:
            p = by_id.get(r[0])
            gross = float(r[4] or 0)
            disc = float(r[1] or 0)
            out.append({
                "id": r[0],
                "name": p.display_name if p else "?",
                "code": (p.default_code or "") if p else "",
                "barcode": (p.barcode or "") if p else "",
                "qty": float(r[3] or 0),
                "gross": gross,
                "discount": disc,
                "net": float(r[2] or 0),
                "avg_pct": disc / gross * 100.0 if gross else 0.0,
            })
        return out

    @api.model
    def _discount_people(self, configs, date_from, date_to, limit=25):
        """Kim chegirma berdi — sotuvchi bo'lsa sotuvchi, bo'lmasa kassir."""
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)

        info = self.env["feliza.detect"].salesperson_info()
        variants = []
        if info and info.get("on_line"):
            variants.append((info["field"], "l", info["comodel"]))
        elif info:
            variants.append((info["field"], "o", info["comodel"]))
        # zaxira: kassir (pos.order.user_id) — sotuvchi maydoni bo'sh bo'lsa
        variants.append(("user_id", "o", "res.users"))

        query = """
            SELECT {t}.{f} AS person,
                   SUM(l.price_unit * l.qty * l.discount / 100.0) AS disc,
                   SUM(l.price_subtotal_incl)                     AS net,
                   COUNT(DISTINCT o.id)                           AS orders,
                   COUNT(DISTINCT o.id) FILTER (WHERE l.discount > 0) AS disc_orders,
                   MAX(l.discount)                                AS max_pct
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
               AND {t}.{f} IS NOT NULL
             GROUP BY 1
             HAVING SUM(l.price_unit * l.qty * l.discount / 100.0) > 0
             ORDER BY disc DESC
             LIMIT %s
        """

        rows, comodel = [], "res.users"
        for field, table, model in variants:
            try:
                self.env.cr.execute(
                    query.format(t=table, f=field),
                    (configs.ids, list(POS_DONE_STATES), dt_from, dt_to, limit))
                rows = self.env.cr.fetchall()
            except Exception:
                self.env.cr.rollback()
                rows = []
            if rows:
                comodel = model
                break
        if not rows:
            return []

        recs = self.env[comodel].sudo().browse([r[0] for r in rows])
        by_id = {r.id: r for r in recs}
        out = []
        for r in rows:
            disc = float(r[1] or 0)
            net = float(r[2] or 0)
            gross = net + disc
            rec = by_id.get(r[0])
            out.append({
                "id": r[0],
                "model": comodel,
                "name": rec.display_name if rec else "?",
                "discount": disc,
                "net": net,
                "pct": disc / gross * 100.0 if gross else 0.0,
                "orders": int(r[3] or 0),
                "disc_orders": int(r[4] or 0),
                "max_pct": float(r[5] or 0),
            })
        return out

    @api.model
    def _discount_buckets(self, configs, date_from, date_to):
        """Chegirma foizi bo'yicha taqsimot."""
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)

        self.env.cr.execute("""
            SELECT CASE
                     WHEN l.discount <= 10 THEN '1-10%%'
                     WHEN l.discount <= 20 THEN '11-20%%'
                     WHEN l.discount <= 30 THEN '21-30%%'
                     WHEN l.discount <= 50 THEN '31-50%%'
                     ELSE '50%%+'
                   END AS bucket,
                   COUNT(*)                                        AS lines,
                   SUM(l.qty)                                      AS qty,
                   SUM(l.price_unit * l.qty * l.discount / 100.0)   AS disc
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
               AND l.discount > 0
             GROUP BY 1
        """, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))

        order = {"1-10%": 1, "11-20%": 2, "21-30%": 3, "31-50%": 4, "50%+": 5}
        rows = [{
            "label": r[0],
            "lines": int(r[1] or 0),
            "qty": float(r[2] or 0),
            "discount": float(r[3] or 0),
        } for r in self.env.cr.fetchall()]
        rows.sort(key=lambda x: order.get(x["label"], 9))
        return rows

    @api.model
    def _discount_orders(self, configs, date_from, date_to, limit=25):
        """Chegirmali cheklar ro'yxati — tekshirish uchun."""
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)

        self.env.cr.execute("""
            SELECT o.id, o.pos_reference, o.date_order, o.config_id,
                   o.amount_total,
                   SUM(l.price_unit * l.qty * l.discount / 100.0) AS disc,
                   MAX(l.discount)                                AS max_pct,
                   SUM(l.qty)                                     AS qty
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
             GROUP BY o.id, o.pos_reference, o.date_order, o.config_id, o.amount_total
            HAVING SUM(l.price_unit * l.qty * l.discount / 100.0) > 0
             ORDER BY o.date_order DESC
             LIMIT %s
        """, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to, limit))
        rows = self.env.cr.fetchall()
        if not rows:
            return []

        cfgs = self.env["pos.config"].sudo().browse(list({r[3] for r in rows}))
        cfg_name = {c.id: ((c.feliza_store_group or "").strip() or c.name)
                    for c in cfgs}
        tz = self._tz()

        out = []
        for r in rows:
            dt = r[2]
            local = pytz.UTC.localize(dt).astimezone(tz) if dt else None
            disc = float(r[5] or 0)
            total = float(r[4] or 0)
            out.append({
                "id": r[0],
                "ref": r[1] or "",
                "date": local.strftime("%d.%m %H:%M") if local else "",
                "store": cfg_name.get(r[3], "?"),
                "total": total,
                "discount": disc,
                "max_pct": float(r[6] or 0),
                "qty": float(r[7] or 0),
                "pct": disc / (total + disc) * 100.0 if (total + disc) else 0.0,
            })
        return out

    # ================================================================== #
    #  SOTUVLAR RO'YXATI — kassa/do'kon bo'yicha to'liq (qator darajasida) #
    #                                                                      #
    #  Har qator = bitta sotilgan mahsulot: TR (chek), vaqti, do'kon,       #
    #  mahsulot to'liq nomi, soni, summasi, sotuvchisi. Yuqoridagi umumiy   #
    #  davr + do'kon filtri, hamda qidiruv va sotuvchi filtri bilan.        #
    #  Katta hajm: server oxirgi `limit` qatorni beradi, umumiy son/summa   #
    #  esa alohida hisoblanadi; to'liq ro'yxat — Excel orqali.              #
    # ================================================================== #
    @api.model
    def _sales_seller_fields(self):
        """(sotuvchi_field, sotuvchi_comodel, kassir_field, kassir_comodel,
        fallbackmi) — hammasi order (pos.order) darajasida."""
        Detect = self.env["feliza.detect"]
        sp = Detect.salesperson_info()
        cash = Detect.cashier_info()
        seller_f = sp["field"] if (sp and not sp["on_line"]) else None
        seller_co = (sp or {}).get("comodel") or "hr.employee"
        cash_f = cash["field"] if (cash and not cash["on_line"]) else None
        cash_co = (cash or {}).get("comodel") or "hr.employee"
        return seller_f, seller_co, cash_f, cash_co, bool(sp and sp.get("is_fallback"))

    @api.model
    def _sales_where(self, configs, dt_from, dt_to, query, seller, seller_f):
        """Umumiy WHERE + parametrlar (psycopg2 %s). SQL in'ektsiyaga yo'l yo'q:
        seller_f — server aniqlagan ustun nomi, qiymatlar esa parametr."""
        where = ("WHERE o.config_id = ANY(%s) AND o.state = ANY(%s) "
                 "AND o.date_order >= %s AND o.date_order <= %s AND l.qty <> 0")
        params = [configs.ids, list(POS_DONE_STATES), dt_from, dt_to]
        if query and query.strip():
            like = "%" + query.strip() + "%"
            where += (" AND (l.full_product_name ILIKE %s "
                      "OR o.pos_reference ILIKE %s OR o.name ILIKE %s)")
            params += [like, like, like]
        if seller and seller_f:
            where += " AND o.%s = %%s" % seller_f
            params.append(int(seller))
        return where, params

    @api.model
    def get_sales_list(self, period="today", date_from=None, date_to=None,
                       store=None, query="", seller=None, limit=1000):
        self._check_sales_access()
        d_from, d_to = self._period_dates(period, date_from, date_to)
        configs = self._scoped_configs(store)
        out = {"period": {"from": str(d_from), "to": str(d_to), "key": period},
               "rows": [], "count": 0, "shown": 0, "total": 0.0, "qty": 0.0,
               "sellers": [], "limit": int(limit), "seller_label": "Sotuvchi",
               "show_cashier": False}
        if not configs:
            return out
        try:
            limit = max(1, min(int(limit), 5000))
        except (TypeError, ValueError):
            limit = 1000
        out["limit"] = limit
        dt_from, dt_to = self._bounds(d_from, d_to)
        seller_f, seller_co, cash_f, cash_co, is_fallback = \
            self._sales_seller_fields()
        out["seller_label"] = "Kassir" if is_fallback else "Sotuvchi"
        out["show_cashier"] = bool(cash_f and not is_fallback)

        where, params = self._sales_where(
            configs, dt_from, dt_to, query, seller, seller_f)

        # Umumiy son + summa + dona (limitdan qat'iy nazar)
        self.env.cr.execute(
            "SELECT COUNT(*), COALESCE(SUM(l.qty),0), "
            "COALESCE(SUM(l.price_subtotal_incl),0) "
            "FROM pos_order_line l JOIN pos_order o ON o.id = l.order_id " + where,
            tuple(params))
        cnt, qty_tot, amt_tot = self.env.cr.fetchone()
        out["count"] = int(cnt or 0)
        out["qty"] = float(qty_tot or 0)
        out["total"] = float(amt_tot or 0)

        seller_sel = ("o.%s" % seller_f) if seller_f else "NULL::integer"
        cash_sel = ("o.%s" % cash_f) if cash_f else "NULL::integer"
        sql = (
            "SELECT o.id, o.name, o.pos_reference, o.date_order, o.config_id, "
            "       l.full_product_name, l.qty, l.price_subtotal_incl, "
            "       l.discount, {ss} AS seller_id, {cs} AS cashier_id, "
            "       l.product_id, o.partner_id "
            "  FROM pos_order_line l JOIN pos_order o ON o.id = l.order_id "
            + where +
            " ORDER BY o.date_order DESC, o.id DESC, l.id LIMIT %s"
        ).format(ss=seller_sel, cs=cash_sel)
        self.env.cr.execute(sql, tuple(params) + (limit,))
        rows = self.env.cr.fetchall()

        cfgs = self.env["pos.config"].sudo().browse(list({r[4] for r in rows}))
        cfg_name = {c.id: ((c.feliza_store_group or "").strip() or c.name)
                    for c in cfgs}
        emp_ids = {r[9] for r in rows if r[9]} | {r[10] for r in rows if r[10]}
        emp_name = {}
        if emp_ids:
            model = self.env["hr.employee"].sudo() if "hr.employee" in self.env \
                else None
            if model is not None:
                for e in model.browse(list(emp_ids)):
                    emp_name[e.id] = e.name or e.display_name

        # Mahsulot nomini toza (atributsiz) + rang/o'lcham alohida
        prod_ids = list({r[11] for r in rows if r[11]})
        tmpl_name = {}
        if prod_ids:
            for p in self.env["product.product"].sudo().browse(prod_ids):
                tmpl_name[p.id] = (p.product_tmpl_id.name or "").strip()
        attrs_map = self._variant_attrs(prod_ids)

        part_ids = list({r[12] for r in rows if r[12]})
        part_name = {}
        if part_ids:
            for pa in self.env["res.partner"].sudo().browse(part_ids):
                part_name[pa.id] = pa.name or ""

        tz = self._tz()
        out_rows = []
        for r in rows:
            dt = r[3]
            local = pytz.UTC.localize(dt).astimezone(tz) if dt else None
            pid = r[11]
            d = attrs_map.get(pid) or {}
            size = d.get("size") or ""
            other = d.get("other") or []
            if other:
                extra = ", ".join(other)
                size = (size + " · " + extra) if size else extra
            out_rows.append({
                "id": r[0],
                "ref": (r[1] or r[2] or "").strip(),
                "ref2": r[2] or "",
                "time": local.strftime("%d.%m.%Y %H:%M") if local else "",
                "store": cfg_name.get(r[4], "?"),
                "product": tmpl_name.get(pid) or (r[5] or ""),
                "rang": d.get("color") or "",
                "olcham": size,
                "qty": float(r[6] or 0),
                "amount": float(r[7] or 0),
                "discount": float(r[8] or 0),
                "seller": emp_name.get(r[9], "—") if r[9] else "—",
                "cashier": emp_name.get(r[10], "—") if r[10] else "—",
                "customer": part_name.get(r[12], "—") if r[12] else "—",
            })
        out["rows"] = out_rows
        out["shown"] = len(out_rows)

        # Sotuvchi filtri uchun ro'yxat (joriy davr + do'kon bo'yicha)
        if seller_f:
            self.env.cr.execute(
                ("SELECT DISTINCT o.{sf} FROM pos_order o "
                 "WHERE o.config_id = ANY(%s) AND o.state = ANY(%s) "
                 "AND o.date_order >= %s AND o.date_order <= %s "
                 "AND o.{sf} IS NOT NULL").format(sf=seller_f),
                (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))
            sids = [x[0] for x in self.env.cr.fetchall()]
            smap = {}
            if sids and seller_co in self.env:
                for e in self.env[seller_co].sudo().browse(sids):
                    smap[e.id] = e.name or e.display_name
            out["sellers"] = sorted(
                [{"id": i, "name": smap.get(i, "?")} for i in sids],
                key=lambda d: d["name"] or "")
        return out

    @api.model
    def export_sales_xlsx(self, period="today", date_from=None, date_to=None,
                          store=None, query="", seller=None):
        """Filtrlangan to'liq sotuv ro'yxatini Excel qilib beradi (yuklab olish
        havolasi qaytadi). Ekrandagi filtrlar bilan bir xil natija."""
        import io
        import base64
        from odoo.exceptions import UserError
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("Excel kutubxonasi (xlsxwriter) o'rnatilmagan."))

        self._check_sales_access()
        d_from, d_to = self._period_dates(period, date_from, date_to)
        configs = self._scoped_configs(store)
        if not configs:
            raise UserError(_("Ko'rsatadigan sotuv topilmadi."))
        dt_from, dt_to = self._bounds(d_from, d_to)
        seller_f, seller_co, cash_f, cash_co, is_fallback = \
            self._sales_seller_fields()
        where, params = self._sales_where(
            configs, dt_from, dt_to, query, seller, seller_f)
        seller_sel = ("o.%s" % seller_f) if seller_f else "NULL::integer"
        cash_sel = ("o.%s" % cash_f) if cash_f else "NULL::integer"
        sql = (
            "SELECT o.name, o.pos_reference, o.date_order, o.config_id, "
            "       l.full_product_name, l.qty, l.price_subtotal_incl, "
            "       l.discount, {ss} AS seller_id, {cs} AS cashier_id, "
            "       l.product_id, o.partner_id "
            "  FROM pos_order_line l JOIN pos_order o ON o.id = l.order_id "
            + where +
            " ORDER BY o.date_order DESC, o.id DESC, l.id LIMIT 100000"
        ).format(ss=seller_sel, cs=cash_sel)
        self.env.cr.execute(sql, tuple(params))
        rows = self.env.cr.fetchall()

        cfgs = self.env["pos.config"].sudo().browse(list({r[3] for r in rows}))
        cfg_name = {c.id: ((c.feliza_store_group or "").strip() or c.name)
                    for c in cfgs}
        emp_ids = {r[8] for r in rows if r[8]} | {r[9] for r in rows if r[9]}
        emp_name = {}
        if emp_ids and "hr.employee" in self.env:
            for e in self.env["hr.employee"].sudo().browse(list(emp_ids)):
                emp_name[e.id] = e.name or e.display_name
        # Mahsulot nomi (toza, atributsiz) + atributlarni alohida ustunga
        prod_ids = list({r[10] for r in rows if r[10]})
        tmpl_name = {}
        if prod_ids:
            for p in self.env["product.product"].sudo().browse(prod_ids):
                tmpl_name[p.id] = (p.product_tmpl_id.name or "").strip()
        attrs_map = self._variant_attrs(prod_ids)
        part_ids = list({r[11] for r in rows if r[11]})
        part_name = {}
        if part_ids:
            for pa in self.env["res.partner"].sudo().browse(part_ids):
                part_name[pa.id] = pa.name or ""

        def _rang(pid):
            return (attrs_map.get(pid) or {}).get("color") or ""

        def _olcham(pid):
            d = attrs_map.get(pid) or {}
            size = d.get("size") or ""
            other = d.get("other") or []
            if other:
                extra = ", ".join(other)
                size = (size + " · " + extra) if size else extra
            return size
        tz = self._tz()
        seller_lbl = "Kassir" if is_fallback else "Sotuvchi"

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        ws = wb.add_worksheet("Sotuvlar")
        f_hdr = wb.add_format({"bold": True, "bg_color": "#1f2937",
                               "font_color": "#ffffff", "border": 1,
                               "align": "center", "valign": "vcenter"})
        f_txt = wb.add_format({"border": 1})
        f_num = wb.add_format({"border": 1, "num_format": "#,##0"})
        f_qty = wb.add_format({"border": 1, "num_format": "0.###"})
        f_tot = wb.add_format({"bold": True, "border": 1, "num_format": "#,##0",
                               "bg_color": "#e5e7eb"})
        f_totl = wb.add_format({"bold": True, "border": 1, "bg_color": "#e5e7eb"})

        headers = ["#", "TR (chek)", "Sana / vaqt", "Do'kon", "Mahsulot",
                   "Rang", "O'lcham", "Soni", "Summa", "Chegirma %", seller_lbl,
                   "Kassir", "Mijoz"]
        widths = [5, 18, 17, 14, 34, 14, 10, 7, 13, 10, 20, 20, 24]
        for c, (h, w) in enumerate(zip(headers, widths)):
            ws.set_column(c, c, w)
            ws.write(0, c, h, f_hdr)
        ws.freeze_panes(1, 0)

        r = 1
        qsum = 0.0
        asum = 0.0
        for row in rows:
            dt = row[2]
            local = pytz.UTC.localize(dt).astimezone(tz) if dt else None
            qty = float(row[5] or 0)
            amt = float(row[6] or 0)
            qsum += qty
            asum += amt
            ws.write_number(r, 0, r, f_txt)
            ws.write_string(r, 1, (row[0] or row[1] or ""), f_txt)
            ws.write_string(r, 2, local.strftime("%d.%m.%Y %H:%M") if local
                            else "", f_txt)
            ws.write_string(r, 3, cfg_name.get(row[3], "?"), f_txt)
            pid = row[10]
            ws.write_string(r, 4, tmpl_name.get(pid) or (row[4] or ""), f_txt)
            ws.write_string(r, 5, _rang(pid), f_txt)
            ws.write_string(r, 6, _olcham(pid), f_txt)
            ws.write_number(r, 7, qty, f_qty)
            ws.write_number(r, 8, amt, f_num)
            ws.write_number(r, 9, float(row[7] or 0), f_qty)
            ws.write_string(r, 10, emp_name.get(row[8], "—") if row[8] else "—",
                            f_txt)
            ws.write_string(r, 11, emp_name.get(row[9], "—") if row[9] else "—",
                            f_txt)
            ws.write_string(r, 12, part_name.get(row[11], "—") if row[11]
                            else "—", f_txt)
            r += 1
        ws.write_string(r, 4, "JAMI", f_totl)
        ws.write_number(r, 7, qsum, f_tot)
        ws.write_number(r, 8, asum, f_tot)
        for c in (0, 1, 2, 3, 5, 6, 9, 10, 11, 12):
            ws.write_blank(r, c, None, f_totl)
        wb.close()
        data = buf.getvalue()

        fname = "Sotuvlar_%s_%s.xlsx" % (d_from, d_to)
        att = self.env["ir.attachment"].sudo().create({
            "name": fname,
            "type": "binary",
            "datas": base64.b64encode(data),
            "mimetype": ("application/vnd.openxmlformats-officedocument."
                         "spreadsheetml.sheet"),
        })
        return {"type": "ir.actions.act_url",
                "url": "/web/content/%d?download=true" % att.id,
                "target": "self"}

    def export_staff_xlsx(self, period="month", date_from=None, date_to=None,
                          store=None, which="both"):
        """Xodimlarni Excelга chiqaradi. which='sellers' (faqat sotuvchilar),
        'cashiers' (faqat kassirlar), 'both' (ikkalasi — 2 varaq). Ekrandagi
        filtrlar (davr + do'kon) bilan aynan bir xil (get_staff qayta ishlatiladi)."""
        import io
        import base64
        from odoo.exceptions import UserError
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("Excel kutubxonasi (xlsxwriter) o'rnatilmagan."))

        # CHIDAMLILIK: brauzerda eski JS (periodArgs 2-elementli) keshda qolsa,
        # argumentlar siljib keladi: [None, None, <do'kon>, <which>] — ya'ni
        # haqiqiy do'kon `date_to` slotiga, `which` esa `store` slotiga tushadi.
        # Buni aniqlab to'g'rilaymiz, shunda qaysi JS bo'lsa ham filtr ishlaydi.
        if store in ("both", "sellers", "cashiers"):
            which = store
            store = date_to or None      # eski JS: haqiqiy do'kon date_to da
            date_to = None
            if not period:
                period = "today"

        data = self.get_staff(period, date_from, date_to, store)
        d_from = data["period"]["from"]
        d_to = data["period"]["to"]
        sellers = data.get("salespeople") or []
        cashiers = data.get("cashiers") or []

        # Har sotuvchi qaysi do'kon(lar)da — umumiy eksportda ham ko'rinsin
        sp_stores = {}
        configs = self._scoped_configs(store)
        sp_info = self.env["feliza.detect"].salesperson_info()
        if (sp_info and not sp_info.get("is_fallback") and configs and sellers):
            dt_from, dt_to = self._bounds(
                fields.Date.to_date(d_from), fields.Date.to_date(d_to))
            fld = sp_info["field"]
            if sp_info["on_line"]:
                sql = ("SELECT l.{f} AS sp, ARRAY_AGG(DISTINCT COALESCE("
                       "NULLIF(c.feliza_store_group,''), "
                       "NULLIF(c.feliza_store_name,''), c.name)) "
                       "FROM pos_order_line l "
                       "JOIN pos_order o ON o.id = l.order_id "
                       "JOIN pos_config c ON c.id = o.config_id "
                       "WHERE o.config_id = ANY(%s) AND o.state = ANY(%s) "
                       "AND o.date_order >= %s AND o.date_order <= %s "
                       "AND l.{f} IS NOT NULL GROUP BY 1").format(f=fld)
            else:
                sql = ("SELECT o.{f} AS sp, ARRAY_AGG(DISTINCT COALESCE("
                       "NULLIF(c.feliza_store_group,''), "
                       "NULLIF(c.feliza_store_name,''), c.name)) "
                       "FROM pos_order o "
                       "JOIN pos_config c ON c.id = o.config_id "
                       "WHERE o.config_id = ANY(%s) AND o.state = ANY(%s) "
                       "AND o.date_order >= %s AND o.date_order <= %s "
                       "AND o.{f} IS NOT NULL GROUP BY 1").format(f=fld)
            try:
                self.env.cr.execute(
                    sql, (configs.ids, list(POS_DONE_STATES), dt_from, dt_to))
                for spid, stores in self.env.cr.fetchall():
                    names = [s for s in (stores or []) if s]
                    sp_stores[spid] = (", ".join(names[:2])
                                       + ("…" if len(names) > 2 else ""))
            except Exception:
                sp_stores = {}

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        f_hdr = wb.add_format({"bold": True, "bg_color": "#1f2937",
                               "font_color": "#ffffff", "border": 1,
                               "align": "center", "valign": "vcenter"})
        f_txt = wb.add_format({"border": 1})
        f_num = wb.add_format({"border": 1, "num_format": "#,##0"})
        f_flt = wb.add_format({"border": 1, "num_format": "0.00"})
        f_tot = wb.add_format({"bold": True, "border": 1, "num_format": "#,##0",
                               "bg_color": "#e5e7eb"})
        f_totl = wb.add_format({"bold": True, "border": 1,
                                "bg_color": "#e5e7eb"})
        f_title = wb.add_format({"bold": True, "font_size": 12,
                                 "align": "left", "valign": "vcenter"})
        store_lbl = store or _("Barcha do'konlar")

        def _sheet_sellers():
            ws = wb.add_worksheet("Sotuvchilar")
            heads = ["#", "Sotuvchi", "Do'kon", "Tushum", "Chek",
                     "O'rt. chek", "UPT"]
            widths = [5, 30, 20, 15, 8, 14, 8]
            ws.merge_range(
                0, 0, 0, len(heads) - 1,
                "Sotuvchilar · Do'kon: %s · Davr: %s – %s"
                % (store_lbl, d_from, d_to), f_title)
            for c, (h, w) in enumerate(zip(heads, widths)):
                ws.set_column(c, c, w)
                ws.write(1, c, h, f_hdr)
            ws.freeze_panes(2, 0)
            r = 2
            idx = 0
            rev_sum = 0.0
            chk_sum = 0
            for row in sellers:
                idx += 1
                rev = float(row.get("revenue") or 0)
                chk = int(row.get("orders") or 0)
                rev_sum += rev
                chk_sum += chk
                ws.write_number(r, 0, idx, f_txt)
                ws.write_string(r, 1, row.get("name") or "", f_txt)
                ws.write_string(r, 2, sp_stores.get(row.get("id"), ""), f_txt)
                ws.write_number(r, 3, rev, f_num)
                ws.write_number(r, 4, chk, f_txt)
                ws.write_number(r, 5, float(row.get("avg_check") or 0), f_num)
                ws.write_number(r, 6, float(row.get("upt") or 0), f_flt)
                r += 1
            ws.write_string(r, 1, "JAMI", f_totl)
            ws.write_number(r, 3, rev_sum, f_tot)
            ws.write_number(r, 4, chk_sum, f_tot)
            for c in (0, 2, 5, 6):
                ws.write_blank(r, c, None, f_totl)

        def _sheet_cashiers():
            ws2 = wb.add_worksheet("Kassirlar")
            heads2 = ["#", "Kassir", "Do'kon", "Chek", "Tushum", "Smena",
                      "Kassa farqi"]
            widths2 = [5, 30, 22, 8, 15, 8, 14]
            ws2.merge_range(
                0, 0, 0, len(heads2) - 1,
                "Kassirlar · Do'kon: %s · Davr: %s – %s"
                % (store_lbl, d_from, d_to), f_title)
            for c, (h, w) in enumerate(zip(heads2, widths2)):
                ws2.set_column(c, c, w)
                ws2.write(1, c, h, f_hdr)
            ws2.freeze_panes(2, 0)
            r = 2
            idx = 0
            rev2 = 0.0
            chk2 = 0
            dif2 = 0.0
            for row in cashiers:
                idx += 1
                rev = float(row.get("revenue") or 0)
                chk = int(row.get("orders") or 0)
                dif = float(row.get("difference") or 0)
                rev2 += rev
                chk2 += chk
                dif2 += dif
                ws2.write_number(r, 0, idx, f_txt)
                ws2.write_string(r, 1, row.get("name") or "", f_txt)
                ws2.write_string(r, 2, row.get("store") or "", f_txt)
                ws2.write_number(r, 3, chk, f_txt)
                ws2.write_number(r, 4, rev, f_num)
                ws2.write_number(r, 5, int(row.get("sessions") or 0), f_txt)
                ws2.write_number(r, 6, dif, f_num)
                r += 1
            ws2.write_string(r, 1, "JAMI", f_totl)
            ws2.write_number(r, 3, chk2, f_tot)
            ws2.write_number(r, 4, rev2, f_tot)
            ws2.write_number(r, 6, dif2, f_tot)
            for c in (0, 2, 5):
                ws2.write_blank(r, c, None, f_totl)

        if which == "sellers":
            _sheet_sellers()
            label = "Sotuvchilar"
        elif which == "cashiers":
            _sheet_cashiers()
            label = "Kassirlar"
        else:
            _sheet_sellers()
            _sheet_cashiers()
            label = "Xodimlar"

        wb.close()
        out = buf.getvalue()
        store_part = (store or "Barcha").replace(" ", "_").replace("'", "") \
            .replace("`", "").replace("/", "-")
        if d_from == d_to:
            fname = "%s_%s_%s.xlsx" % (label, store_part, d_from)
        else:
            fname = "%s_%s_%s_%s.xlsx" % (label, store_part, d_from, d_to)
        att = self.env["ir.attachment"].sudo().create({
            "name": fname, "type": "binary",
            "datas": base64.b64encode(out),
            "mimetype": ("application/vnd.openxmlformats-officedocument."
                         "spreadsheetml.sheet"),
        })
        return {"type": "ir.actions.act_url",
                "url": "/web/content/%d?download=true" % att.id,
                "target": "self"}


    # ================================================================== #
    #  6 · DO'KON BO'YICHA QOLDIQ                                         #
    # ================================================================== #
    @api.model
    def _stock_warehouses(self, store=None):
        """Qoldiq ko'rsatiladigan omborlar.

        Rahbar    → kompaniyaning BARCHA omborlari (asosiy ombor ham)
        Do'kon b. → faqat o'z kassasiga bog'langan ombor
        """
        Wh = self.env["stock.warehouse"].sudo()
        if self._is_manager():
            whs = Wh.search([("company_id", "in", self.env.companies.ids)])
            if store:
                scoped = self._scoped_configs(store).mapped(
                    "picking_type_id.warehouse_id")
                whs = scoped or whs.browse()
        elif self._is_store_user():
            whs = self._scoped_configs(store).mapped("picking_type_id.warehouse_id")
        elif self._is_stock_user():
            # ombor xodimi: biriktirilgan omborlar, bo'sh bo'lsa — barchasi
            assigned = self.env.user.sudo().feliza_dashboard_warehouse_ids
            whs = assigned or Wh.search([("company_id", "in", self.env.companies.ids)])
            whs = whs.filtered(lambda w: w.company_id.id in self.env.companies.ids)
        else:
            whs = Wh.browse()
        return whs

    @api.model
    def _loc_to_wh(self, warehouses):
        """{lokatsiya_id: ombor_id} — faqat ichki lokatsiyalar."""
        Loc = self.env["stock.location"].sudo()
        mapping = {}
        for wh in warehouses:
            locs = Loc.search([
                ("id", "child_of", wh.view_location_id.id),
                ("usage", "=", "internal"),
            ])
            for loc in locs:
                mapping[loc.id] = wh.id
        return mapping

    @api.model
    def get_stock_by_store(self, store=None):
        """Har bir ombor/do'kon bo'yicha qoldiq jamlanmasi."""
        self._check_access_dashboard()
        whs = self._stock_warehouses(store)
        if not whs:
            return {"rows": [], "total": {}}

        loc2wh = self._loc_to_wh(whs)
        if not loc2wh:
            return {"rows": [], "total": {}}

        show_cost = self._show_cost()
        company_key = str(self.env.company.id)

        self.env.cr.execute("""
            SELECT q.location_id, q.product_id, SUM(q.quantity) AS qty,
                   MAX(pt.list_price) AS price,
                   MAX((pp.standard_price ->> %s)::numeric) AS cost
              FROM stock_quant q
              JOIN product_product pp ON pp.id = q.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE q.location_id = ANY(%s)
             GROUP BY 1, 2
            HAVING SUM(q.quantity) <> 0
        """, (company_key, list(loc2wh.keys())))

        # (ombor, tovar) darajasida yig'amiz — bir ombor ichida bir necha
        # lokatsiya bo'lishi mumkin, ular qo'shilib bitta natija beradi
        agg = {}
        for loc_id, product_id, qty, price, cost in self.env.cr.fetchall():
            wh_id = loc2wh.get(loc_id)
            if not wh_id:
                continue
            slot = agg.setdefault(wh_id, {})
            cur = slot.setdefault(product_id, [0.0, 0.0, 0.0])
            cur[0] += float(qty or 0)
            cur[1] = float(price or 0)
            cur[2] = float(cost or 0)

        rows = []
        all_products = set()
        for wh in whs:
            slot = agg.get(wh.id) or {}
            skus = units = value = cost_val = 0
            units = value = cost_val = 0.0
            for pid, (q, price, cost) in slot.items():
                if not q:
                    continue           # sof qoldig'i 0 — hisobga olinmaydi
                skus += 1
                all_products.add(pid)
                units += q
                value += q * price
                cost_val += q * cost
            row = {
                "id": wh.id,
                "name": wh.name,
                "code": wh.code,
                "skus": skus,
                "units": units,
                "value": value,
            }
            if show_cost:
                row["cost"] = cost_val
            rows.append(row)

        rows.sort(key=lambda r: r["units"], reverse=True)
        total = {
            "skus": len(all_products),
            "units": sum(r["units"] for r in rows),
            "value": sum(r["value"] for r in rows),
        }
        if show_cost:
            total["cost"] = sum(r.get("cost", 0.0) for r in rows)

        # Hech bir omborga tegishli bo'lmagan ichki qoldiq — amalda bu
        # TRANZIT lokatsiyasi ("Inter Warehouse Transfer"): tovar A
        # ombordan chiqqan, lekin B hali qabul qilmagan. Uni ko'rsatmasak,
        # kompaniyaning umumiy qoldig'i jadvaldagi yig'indidan ko'p bo'lib
        # chiqadi va buxgalter «tovar qayoqqa ketdi?» deb qoladi.
        #
        # DIQQAT: tranzit — KOMPANIYA darajasidagi ko'rsatkich, u hech bir
        # do'konga tegishli emas. Shuning uchun u faqat filtr yo'q va
        # foydalanuvchi barcha omborlarni ko'ra oladigan holatda chiqadi.
        # Aks holda (masalan «Andijon» filtri qo'yilganda) qolgan barcha
        # do'konlarning qoldig'i xato ravishda «tranzit» bo'lib ko'rinardi.
        if not store and self._is_manager():
            total["transit"] = self._stock_unassigned(company_key, show_cost)
            # 100% ANIQ umumiy qo'ldagi tovar — barcha do'konlar bo'yicha.
            # Omborlar xaritasiga bog'liq emas: kompaniyaning BARCHA ichki
            # lokatsiyalari (do'kon omborlari + online + asosiy + tranzit)
            # to'g'ridan-to'g'ri sanaladi -> hech narsa tushib qolmaydi.
            total["grand"] = self._stock_grand_total(company_key, show_cost)
        return {"rows": rows, "total": total}

    @api.model
    def _stock_grand_total(self, company_key, show_cost):
        """Kompaniyaning BARCHA ichki lokatsiyalaridagi qoldiq (100% aniq).

        get_stock_by_store'dagi «total.units» faqat omborga bog'langan
        lokatsiyalarni yig'adi -> tranzit va xaritaga tushmagan ichki joylar
        chetda qoladi. Bu metod esa usage='internal' bo'lgan HAMMA quantni
        oladi, shuning uchun «qo'limizda qancha tovar bor» degan savolga
        to'liq javob beradi.  Faqat rahbar + filtrsiz holatda chaqiriladi.
        """
        self.env.cr.execute("""
            SELECT COALESCE(SUM(q.quantity), 0),
                   COUNT(DISTINCT q.product_id),
                   COALESCE(SUM(q.quantity * pt.list_price), 0),
                   COALESCE(SUM(q.quantity
                                * COALESCE((pp.standard_price ->> %s)::numeric, 0)), 0)
              FROM stock_quant q
              JOIN stock_location l ON l.id = q.location_id
              JOIN product_product pp ON pp.id = q.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE l.usage = 'internal'
               AND q.company_id = ANY(%s)
               AND q.quantity <> 0
        """, (company_key, self.env.companies.ids))
        r = self.env.cr.fetchone() or (0, 0, 0, 0)
        out = {
            "units": float(r[0] or 0),
            "skus": int(r[1] or 0),
            "value": float(r[2] or 0),
        }
        if show_cost:
            out["cost"] = float(r[3] or 0)
        return out

    @api.model
    def _stock_unassigned(self, company_key, show_cost):
        """Hech bir omborga tegishli bo'lmagan ichki lokatsiyalardagi qoldiq.

        «Ma'lum» lokatsiyalar ro'yxati HAR DOIM barcha omborlar bo'yicha
        quriladi — ekrandagi filtrdan qat'i nazar. Aks holda filtrlangan
        do'kondan boshqa hamma narsa «tranzit» deb hisoblanib ketadi.
        """
        Wh = self.env["stock.warehouse"].sudo()
        all_whs = Wh.search([("company_id", "in", self.env.companies.ids)])
        known = list(self._loc_to_wh(all_whs).keys()) or [0]
        self.env.cr.execute("""
            SELECT COALESCE(SUM(q.quantity), 0),
                   COUNT(DISTINCT q.product_id),
                   COALESCE(SUM(q.quantity * pt.list_price), 0),
                   COALESCE(SUM(q.quantity
                                * COALESCE((pp.standard_price ->> %s)::numeric, 0)), 0)
              FROM stock_quant q
              JOIN stock_location l ON l.id = q.location_id
              JOIN product_product pp ON pp.id = q.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE l.usage = 'internal'
               AND q.company_id = ANY(%s)
               AND NOT (q.location_id = ANY(%s))
        """, (company_key, self.env.companies.ids, known))
        r = self.env.cr.fetchone() or (0, 0, 0, 0)
        out = {
            "units": float(r[0] or 0),
            "skus": int(r[1] or 0),
            "value": float(r[2] or 0),
        }
        if show_cost:
            out["cost"] = float(r[3] or 0)
        return out

    @api.model
    def get_stock_detail(self, warehouse_id=None, query="", limit=100,
                         order="value"):
        """Bitta ombor ichidagi tovarlar ro'yxati (yoki qidiruv natijasi)."""
        self._check_access_dashboard()
        whs = self._stock_warehouses()
        if warehouse_id:
            whs = whs.filtered(lambda w: w.id == int(warehouse_id))
        if not whs:
            return {"rows": [], "count": 0, "warehouse": ""}

        loc2wh = self._loc_to_wh(whs)
        if not loc2wh:
            return {"rows": [], "count": 0, "warehouse": whs[:1].name}

        show_cost = self._show_cost()
        company_key = str(self.env.company.id)
        term = (query or "").strip()
        params = [company_key, list(loc2wh.keys())]

        where_extra = ""
        if term:
            # Qidiruv nom / artikul / barkoddan tashqari VARIANT QIYMATLARI
            # (rang, o'lcham) bo'yicha ham ishlaydi: "qora", "XL", "мовий"…
            where_extra = """
               AND (pp.barcode ILIKE %s OR pp.default_code ILIKE %s
                    OR pt.name->>'en_US' ILIKE %s
                    OR EXISTS (
                        SELECT 1
                          FROM product_variant_combination pvc
                          JOIN product_template_attribute_value ptav
                            ON ptav.id = pvc.product_template_attribute_value_id
                          JOIN product_attribute_value pav
                            ON pav.id = ptav.product_attribute_value_id
                         WHERE pvc.product_product_id = pp.id
                           AND COALESCE(
                                 pav.name->>'en_US',
                                 (SELECT v FROM jsonb_each_text(pav.name)
                                    AS t(k, v) LIMIT 1),
                                 '') ILIKE %s))
            """
            like = "%" + term + "%"
            params += [like, like, like, like]

        order_sql = {
            "value": "value DESC",
            "qty": "qty DESC",
            "name": "name ASC",
        }.get(order, "value DESC")

        params.append(limit)
        self.env.cr.execute("""
            SELECT pp.id,
                   COALESCE(pt.name->>'en_US', '') AS name,
                   pp.default_code, pp.barcode,
                   SUM(q.quantity) AS qty,
                   MAX(pt.list_price) AS price,
                   MAX((pp.standard_price ->> %%s)::numeric) AS cost,
                   SUM(q.quantity) * MAX(pt.list_price) AS value
              FROM stock_quant q
              JOIN product_product pp ON pp.id = q.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE q.location_id = ANY(%%s) %s
             GROUP BY pp.id, name, pp.default_code, pp.barcode
            HAVING SUM(q.quantity) <> 0
             ORDER BY %s
             LIMIT %%s
        """ % (where_extra, order_sql), tuple(params))

        fetched = self.env.cr.fetchall()
        attrs = self._variant_attrs([r[0] for r in fetched])

        rows = []
        for r in fetched:
            a = attrs.get(r[0]) or {}
            row = {
                "id": r[0],
                "name": r[1],
                "code": r[2] or "",
                "barcode": r[3] or "",
                "color": a.get("color", ""),
                "size": a.get("size", ""),
                "attrs": ", ".join(a.get("other", [])),
                "qty": float(r[4] or 0),
                "price": float(r[5] or 0),
                "value": float(r[7] or 0),
            }
            if show_cost:
                row["cost_value"] = float(r[4] or 0) * float(r[6] or 0)
            rows.append(row)

        return {
            "rows": rows,
            "count": len(rows),
            "warehouse": ", ".join(whs.mapped("name")),
            "limit": limit,
        }

    # ------------------------------------------------------------------ #
    #  Variant qiymatlari — rang / o'lcham                                #
    # ------------------------------------------------------------------ #
    #  Atributlar NOMI bo'yicha aniqlanadi, ID bo'yicha emas: bazada
    #  eski ("rang", "size") va yangi ("Rang", "O'lcham") atributlar
    #  yonma-yon turishi mumkin, ikkalasi ham to'g'ri tushunilishi kerak.
    #  Apostrof turlicha yozilgani uchun "o'lcham" emas, "lcham" bo'yicha
    #  qidiriladi.
    # ------------------------------------------------------------------ #
    _ATTR_COLOR = ("rang", "цвет", "color", "colour")
    _ATTR_SIZE = ("lcham", "размер", "разм", "size", "рост")

    @api.model
    def _variant_attrs(self, product_ids):
        """{product_id: {'color': str, 'size': str, 'other': [str]}}"""
        res = {}
        ids = [int(i) for i in (product_ids or []) if i]
        if not ids:
            return res
        self.env.cr.execute("""
            SELECT pvc.product_product_id,
                   COALESCE(pa.name->>'en_US',
                            (SELECT v FROM jsonb_each_text(pa.name)
                               AS t(k, v) LIMIT 1), '') AS attr,
                   COALESCE(pav.name->>'en_US',
                            (SELECT v FROM jsonb_each_text(pav.name)
                               AS t2(k, v) LIMIT 1), '') AS val
              FROM product_variant_combination pvc
              JOIN product_template_attribute_value ptav
                ON ptav.id = pvc.product_template_attribute_value_id
              JOIN product_attribute_value pav
                ON pav.id = ptav.product_attribute_value_id
              JOIN product_attribute pa ON pa.id = ptav.attribute_id
             WHERE pvc.product_product_id = ANY(%s)
             ORDER BY pa.sequence NULLS LAST, pa.id
        """, (ids,))
        for pid, attr, val in self.env.cr.fetchall():
            if not val:
                continue
            slot = res.setdefault(pid, {"color": "", "size": "", "other": []})
            low = (attr or "").strip().lower()
            if not slot["color"] and any(k in low for k in self._ATTR_COLOR):
                slot["color"] = val
            elif not slot["size"] and any(k in low for k in self._ATTR_SIZE):
                slot["size"] = val
            else:
                slot["other"].append("%s: %s" % (attr, val) if attr else val)
        return res

    # ================================================================== #
    #  7 · OMBORLAR ARO O'TKAZMA                                          #
    # ================================================================== #
    #  Manba: warehouse_transfer_custom_19v moduli stock.move ga qo'shgan
    #  saqlanadigan maydonlar:
    #      real_source_warehouse_id / real_dest_warehouse_id
    #      interwh_report_status  ('in_transit' | 'arrived')
    #      interwh_report_qty / interwh_report_total_cost
    #  Modul o'rnatilmagan bo'lsa — bo'lim bo'sh qaytadi.
    # ------------------------------------------------------------------ #
    @api.model
    def get_transfers(self, period="month", date_from=None, date_to=None,
                      store=None):
        self._check_access_dashboard()
        if not self.env["feliza.detect"].has_interwh():
            return {"available": False}

        d_from, d_to = self._period_dates(period, date_from, date_to)
        dt_from, dt_to = self._bounds(d_from, d_to)
        whs = self._stock_warehouses(store)
        wh_ids = whs.ids

        return {
            "available": True,
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "kpi": self._transfer_kpi(wh_ids, dt_from, dt_to),
            "flows": self._transfer_flows(wh_ids, dt_from, dt_to),
            "warehouses": self._transfer_by_wh(wh_ids, dt_from, dt_to),
            "in_transit": self._transfer_in_transit(wh_ids),
            "products": self._transfer_products(wh_ids, dt_from, dt_to),
            "history": self._transfer_history(wh_ids, dt_from, dt_to),
        }

    @api.model
    def _transfer_where(self, wh_ids):
        """Ruxsat etilgan omborlar bo'yicha cheklov."""
        if not wh_ids:
            return " AND FALSE", []
        return (" AND (m.real_source_warehouse_id = ANY(%s)"
                "  OR m.real_dest_warehouse_id = ANY(%s))"), [wh_ids, wh_ids]

    @api.model
    def _transfer_kpi(self, wh_ids, dt_from, dt_to):
        show_cost = self._show_cost()
        empty = {"arrived_qty": 0.0, "arrived_docs": 0, "transit_qty": 0.0,
                 "transit_docs": 0, "avg_days": 0.0, "late_docs": 0,
                 "arrived_cost": 0.0, "transit_cost": 0.0}
        if not wh_ids:
            return empty
        cond, params = self._transfer_where(wh_ids)

        # davr ichida yetib borgan
        self.env.cr.execute("""
            SELECT COALESCE(SUM(m.interwh_report_qty), 0),
                   COUNT(DISTINCT m.picking_id),
                   COALESCE(SUM(m.interwh_report_total_cost), 0)
              FROM stock_move m
             WHERE m.interwh_report_status = 'arrived'
               AND m.date >= %s AND m.date <= %s
        """ + cond, [dt_from, dt_to] + params)
        a = self.env.cr.fetchone() or (0, 0, 0)

        # hozir yo'lda (davrga bog'liq emas — joriy holat)
        self.env.cr.execute("""
            SELECT COALESCE(SUM(m.interwh_report_qty), 0),
                   COUNT(DISTINCT m.picking_id),
                   COALESCE(SUM(m.interwh_report_total_cost), 0),
                   COALESCE(AVG(EXTRACT(EPOCH FROM (now() - m.date)) / 86400.0), 0),
                   COUNT(DISTINCT m.picking_id)
                     FILTER (WHERE m.date < now() - interval '5 days')
              FROM stock_move m
             WHERE m.interwh_report_status = 'in_transit'
        """ + cond, params)
        t = self.env.cr.fetchone() or (0, 0, 0, 0, 0)

        res = {
            "arrived_qty": float(a[0] or 0),
            "arrived_docs": int(a[1] or 0),
            "transit_qty": float(t[0] or 0),
            "transit_docs": int(t[1] or 0),
            "avg_days": float(t[3] or 0),
            "late_docs": int(t[4] or 0),
        }
        if show_cost:
            res["arrived_cost"] = float(a[2] or 0)
            res["transit_cost"] = float(t[2] or 0)
        return res

    @api.model
    def _transfer_flows(self, wh_ids, dt_from, dt_to, limit=20):
        """Yo'nalishlar: kimdan kimga."""
        if not wh_ids:
            return []
        cond, params = self._transfer_where(wh_ids)
        show_cost = self._show_cost()

        self.env.cr.execute("""
            SELECT m.real_source_warehouse_id, m.real_dest_warehouse_id,
                   SUM(m.interwh_report_qty)          AS qty,
                   COUNT(DISTINCT m.picking_id)       AS docs,
                   SUM(m.interwh_report_total_cost)   AS cost
              FROM stock_move m
             WHERE m.interwh_report_status = 'arrived'
               AND m.date >= %s AND m.date <= %s
               AND m.real_source_warehouse_id IS NOT NULL
               AND m.real_dest_warehouse_id IS NOT NULL
        """ + cond + """
             GROUP BY 1, 2
             ORDER BY qty DESC
             LIMIT %s
        """, [dt_from, dt_to] + params + [limit])
        rows = self.env.cr.fetchall()
        if not rows:
            return []

        ids = {r[0] for r in rows} | {r[1] for r in rows}
        whs = self.env["stock.warehouse"].sudo().browse(list(ids))
        name = {w.id: w.name for w in whs}

        out = []
        for r in rows:
            item = {
                "source_id": r[0], "dest_id": r[1],
                "source": name.get(r[0], "?"), "dest": name.get(r[1], "?"),
                "qty": float(r[2] or 0),
                "docs": int(r[3] or 0),
            }
            if show_cost:
                item["cost"] = float(r[4] or 0)
            out.append(item)
        return out

    @api.model
    def _transfer_by_wh(self, wh_ids, dt_from, dt_to):
        """Har bir ombor: qancha jo'natdi, qancha qabul qildi, yo'lda nechta."""
        if not wh_ids:
            return []
        show_cost = self._show_cost()

        self.env.cr.execute("""
            SELECT m.real_source_warehouse_id AS wh,
                   SUM(m.interwh_report_qty) FILTER (
                       WHERE m.interwh_report_status = 'arrived'
                         AND m.date >= %s AND m.date <= %s)      AS sent,
                   SUM(m.interwh_report_qty) FILTER (
                       WHERE m.interwh_report_status = 'in_transit') AS transit,
                   SUM(m.interwh_report_total_cost) FILTER (
                       WHERE m.interwh_report_status = 'arrived'
                         AND m.date >= %s AND m.date <= %s)      AS sent_cost
              FROM stock_move m
             WHERE m.real_source_warehouse_id = ANY(%s)
             GROUP BY 1
        """, [dt_from, dt_to, dt_from, dt_to, wh_ids])
        sent = {r[0]: r for r in self.env.cr.fetchall()}

        self.env.cr.execute("""
            SELECT m.real_dest_warehouse_id AS wh,
                   SUM(m.interwh_report_qty) FILTER (
                       WHERE m.interwh_report_status = 'arrived'
                         AND m.date >= %s AND m.date <= %s)      AS got,
                   SUM(m.interwh_report_total_cost) FILTER (
                       WHERE m.interwh_report_status = 'arrived'
                         AND m.date >= %s AND m.date <= %s)      AS got_cost
              FROM stock_move m
             WHERE m.real_dest_warehouse_id = ANY(%s)
             GROUP BY 1
        """, [dt_from, dt_to, dt_from, dt_to, wh_ids])
        got = {r[0]: r for r in self.env.cr.fetchall()}

        whs = self.env["stock.warehouse"].sudo().browse(wh_ids)
        rows = []
        for w in whs:
            s = sent.get(w.id)
            g = got.get(w.id)
            row = {
                "id": w.id,
                "name": w.name,
                "sent": float((s[1] if s else 0) or 0),
                "transit": float((s[2] if s else 0) or 0),
                "received": float((g[1] if g else 0) or 0),
            }
            row["net"] = row["received"] - row["sent"]
            if show_cost:
                row["sent_cost"] = float((s[3] if s else 0) or 0)
                row["received_cost"] = float((g[2] if g else 0) or 0)
            rows.append(row)

        rows = [r for r in rows if r["sent"] or r["received"] or r["transit"]]
        rows.sort(key=lambda r: r["received"] + r["sent"], reverse=True)
        return rows

    @api.model
    def _transfer_in_transit(self, wh_ids, limit=500):
        """Hozir yo'lda turgan hujjatlar (haqiqatan qabul qilinmaganlar).

        Bekor/eski status tufayli allaqachon YETIB BORGAN (qabul hujjati
        'done') o'tkazmalar chiqarib tashlanadi — ular 'yo'lda' emas.
        Limit yuqori: yo'ldagilar soni cheklangan, eng yangilari ham chiqadi.
        """
        if not wh_ids:
            return []
        cond, params = self._transfer_where(wh_ids)
        show_cost = self._show_cost()

        self.env.cr.execute("""
            SELECT m.picking_id,
                   MIN(m.date)                       AS sent_at,
                   SUM(m.interwh_report_qty)         AS qty,
                   COUNT(*)                          AS lines,
                   MIN(m.real_source_warehouse_id)   AS src,
                   MIN(m.real_dest_warehouse_id)     AS dst,
                   SUM(m.interwh_report_total_cost)  AS cost
              FROM stock_move m
              JOIN stock_picking p ON p.id = m.picking_id
             WHERE m.interwh_report_status = 'in_transit'
               AND m.picking_id IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM stock_picking pin
                    WHERE pin.origin = p.name AND pin.state = 'done')
        """ + cond + """
             GROUP BY m.picking_id
             ORDER BY sent_at DESC
             LIMIT %s
        """, params + [limit])
        rows = self.env.cr.fetchall()
        if not rows:
            return []

        pickings = self.env["stock.picking"].sudo().browse([r[0] for r in rows])
        pick = {p.id: p for p in pickings}
        wh_ids_all = {r[4] for r in rows} | {r[5] for r in rows}
        whs = self.env["stock.warehouse"].sudo().browse(
            [i for i in wh_ids_all if i])
        wname = {w.id: w.name for w in whs}

        today = datetime.now()
        out = []
        for r in rows:
            sent_at = r[1]
            days = (today - sent_at).days if sent_at else 0
            item = {
                "id": r[0],
                "name": pick[r[0]].name if r[0] in pick else "?",
                "date": fields.Datetime.to_string(sent_at)[:10] if sent_at else "",
                "source": wname.get(r[4], "?"),
                "dest": wname.get(r[5], "?"),
                "qty": float(r[2] or 0),
                "lines": int(r[3] or 0),
                "days": days,
            }
            if show_cost:
                item["cost"] = float(r[6] or 0)
            out.append(item)
        out.sort(key=lambda x: x["days"], reverse=True)
        return out

    @api.model
    def _transfer_products(self, wh_ids, dt_from, dt_to, limit=15):
        """Eng ko'p o'tkazilgan tovarlar."""
        if not wh_ids:
            return []
        cond, params = self._transfer_where(wh_ids)
        show_cost = self._show_cost()

        self.env.cr.execute("""
            SELECT m.product_id, SUM(m.interwh_report_qty) AS qty,
                   COUNT(DISTINCT m.picking_id) AS docs,
                   SUM(m.interwh_report_total_cost) AS cost
              FROM stock_move m
             WHERE m.interwh_report_status = 'arrived'
               AND m.date >= %s AND m.date <= %s
        """ + cond + """
             GROUP BY 1
             ORDER BY qty DESC
             LIMIT %s
        """, [dt_from, dt_to] + params + [limit])
        rows = self.env.cr.fetchall()
        if not rows:
            return []

        products = self.env["product.product"].sudo().browse([r[0] for r in rows])
        by_id = {p.id: p for p in products}
        out = []
        for r in rows:
            p = by_id.get(r[0])
            item = {
                "id": r[0],
                "name": p.display_name if p else "?",
                "code": (p.default_code or "") if p else "",
                "qty": float(r[1] or 0),
                "docs": int(r[2] or 0),
            }
            if show_cost:
                item["cost"] = float(r[3] or 0)
            out.append(item)
        return out


    @api.model
    def _transfer_history(self, wh_ids, dt_from, dt_to, limit=100):
        """Davr ichida YETIB BORGAN o'tkazmalar tarixi — hujjat kesimida."""
        if not wh_ids:
            return []
        cond, params = self._transfer_where(wh_ids)
        show_cost = self._show_cost()

        self.env.cr.execute("""
            SELECT m.picking_id,
                   MAX(m.date)                        AS arrived,
                   SUM(m.interwh_report_qty)          AS qty,
                   COUNT(*)                           AS lines,
                   MIN(m.real_source_warehouse_id)    AS src,
                   MIN(m.real_dest_warehouse_id)      AS dst,
                   SUM(m.interwh_report_total_cost)   AS cost
              FROM stock_move m
             WHERE m.interwh_report_status = 'arrived'
               AND m.date >= %s AND m.date <= %s
               AND m.picking_id IS NOT NULL
        """ + cond + """
             GROUP BY m.picking_id
             ORDER BY arrived DESC
             LIMIT %s
        """, [dt_from, dt_to] + params + [limit])
        rows = self.env.cr.fetchall()
        if not rows:
            return []

        pickings = self.env["stock.picking"].sudo().browse([r[0] for r in rows])
        pick = {p.id: p for p in pickings}
        wh_all = {r[4] for r in rows} | {r[5] for r in rows}
        whs = self.env["stock.warehouse"].sudo().browse([i for i in wh_all if i])
        wname = {w.id: w.name for w in whs}
        tz = self._tz()

        out = []
        for r in rows:
            dt = r[1]
            local = pytz.UTC.localize(dt).astimezone(tz) if dt else None
            p = pick.get(r[0])
            item = {
                "id": r[0],
                "name": p.name if p else "?",
                "date": local.strftime("%d.%m.%Y %H:%M") if local else "",
                "source": wname.get(r[4], "?"),
                "dest": wname.get(r[5], "?"),
                "qty": float(r[2] or 0),
                "lines": int(r[3] or 0),
                "origin": (p.origin or "") if p else "",
                "user": (p.user_id.display_name or "") if p and p.user_id else "",
            }
            if show_cost:
                item["cost"] = float(r[6] or 0)
            out.append(item)
        return out

    # ------------------------------------------------------------------ #
    #  Bitta o'tkazma to'liq detali (qatorga bosganda ochiladigan panel)  #
    # ------------------------------------------------------------------ #
    @api.model
    def get_transfer_detail(self, picking_id):
        """Bitta o'tkazma (qabul pickingi) to'liq detali: sarlavha + tovarlar.
        Qayerdan->qayerga, yuborilgan/kelgan sana, kim yubordi/qabul qildi,
        va tovarlar ro'yxati (nom + atributlar + soni [+ tan narx])."""
        self._check_access_dashboard()
        from odoo.exceptions import AccessError
        pk = self.env["stock.picking"].sudo().browse(int(picking_id))
        if not pk.exists():
            return {"ok": False}
        moves = pk.move_ids.filtered(
            lambda m: m.interwh_report_status in ("arrived", "in_transit"))
        if not moves:
            moves = pk.move_ids
        first = moves[:1]
        src_wh = first.real_source_warehouse_id
        dst_wh = first.real_dest_warehouse_id
        # Ruxsat: o'tkazma omborlari foydalanuvchi ko'ra oladiganlar ichida
        allowed = set(self._stock_warehouses(None).ids)
        if allowed and dst_wh.id not in allowed and src_wh.id not in allowed:
            raise AccessError(_("Bu o'tkazmani ko'rish huquqingiz yo'q."))
        # Jo'natma (OUT) pickingini topamiz — move zanjiri, keyin origin nomi
        out_pk = moves.move_orig_ids.picking_id[:1]
        if not out_pk and pk.origin:
            out_pk = self.env["stock.picking"].sudo().search(
                [("name", "=", pk.origin)], limit=1)
        tz = self._tz()

        def _fmt(dt):
            if not dt:
                return ""
            return pytz.UTC.localize(dt).astimezone(tz).strftime(
                "%d.%m.%Y %H:%M")

        show_cost = self._show_cost()
        pids = moves.mapped("product_id").ids
        attrs_map = self._variant_attrs(pids)

        def _attr(pid):
            d = attrs_map.get(pid) or {}
            return ", ".join([x for x in (d.get("color"), d.get("size")) if x]
                             + (d.get("other") or []))

        agg = {}
        for m in moves:
            slot = agg.setdefault(m.product_id.id, {"qty": 0.0, "cost": 0.0})
            slot["qty"] += m.interwh_report_qty or m.quantity or 0.0
            slot["cost"] += m.interwh_report_total_cost or 0.0
        lines = []
        for pid, v in agg.items():
            p = self.env["product.product"].sudo().browse(pid)
            row = {"name": p.product_tmpl_id.name or p.display_name,
                   "attrs": _attr(pid), "code": p.default_code or "",
                   "qty": round(v["qty"], 3)}
            if show_cost:
                row["cost"] = round(v["cost"], 2)
            lines.append(row)
        lines.sort(key=lambda x: -x["qty"])

        res = {
            "ok": True,
            "id": pk.id,
            "in_name": pk.name,
            "out_name": out_pk.name if out_pk else (pk.origin or ""),
            "source": src_wh.name or "?",
            "dest": dst_wh.name or "?",
            "sent_at": _fmt(out_pk.date_done or out_pk.scheduled_date)
                       if out_pk else "",
            "arrived_at": _fmt(pk.date_done or pk.scheduled_date),
            "sender": (out_pk.user_id.display_name
                       or out_pk.create_uid.display_name) if out_pk else "",
            "receiver": (pk.user_id.display_name
                         or pk.create_uid.display_name or ""),
            "lines": lines,
            "total_qty": round(sum(x["qty"] for x in lines), 3),
        }
        if show_cost:
            res["total_cost"] = round(sum(x.get("cost", 0) for x in lines), 2)
        return res

    @api.model
    def export_transfer_xlsx(self, picking_id):
        """Bitta o'tkazmani Excel qilib beradi (sarlavha + tovarlar)."""
        import io
        import base64
        from odoo.exceptions import UserError
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("Excel kutubxonasi (xlsxwriter) o'rnatilmagan."))
        d = self.get_transfer_detail(picking_id)
        if not d.get("ok"):
            raise UserError(_("O'tkazma topilmadi."))
        show_cost = "total_cost" in d

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        ws = wb.add_worksheet("O'tkazma")
        f_lbl = wb.add_format({"bold": True, "bg_color": "#e5e7eb", "border": 1})
        f_val = wb.add_format({"border": 1})
        f_hdr = wb.add_format({"bold": True, "bg_color": "#1f2937",
                               "font_color": "#ffffff", "border": 1,
                               "align": "center"})
        f_txt = wb.add_format({"border": 1})
        f_num = wb.add_format({"border": 1, "num_format": "#,##0"})
        f_qty = wb.add_format({"border": 1, "num_format": "0.###"})
        f_tot = wb.add_format({"bold": True, "border": 1,
                               "num_format": "#,##0", "bg_color": "#e5e7eb"})
        ws.set_column(0, 0, 22)
        ws.set_column(1, 1, 34)
        ws.set_column(2, 2, 22)
        ws.set_column(3, 4, 14)
        pairs = [
            ("Hujjat (qabul)", d["in_name"]),
            ("Hujjat (jo'natma)", d["out_name"]),
            ("Qayerdan", d["source"]), ("Qayerga", d["dest"]),
            ("Yuborilgan", d["sent_at"]), ("Yetib kelgan", d["arrived_at"]),
            ("Kim yubordi", d["sender"]), ("Kim qabul qildi", d["receiver"]),
        ]
        r = 0
        for lbl, val in pairs:
            ws.write_string(r, 0, lbl, f_lbl)
            ws.write_string(r, 1, str(val or ""), f_val)
            r += 1
        r += 1
        cols = ["#", "Mahsulot", "Atributlar", "Soni"]
        if show_cost:
            cols.append("Summa (tan)")
        for c, h in enumerate(cols):
            ws.write(r, c, h, f_hdr)
        r += 1
        i = 1
        for ln in d["lines"]:
            ws.write_number(r, 0, i, f_txt)
            ws.write_string(r, 1, ln["name"] or "", f_txt)
            ws.write_string(r, 2, ln["attrs"] or "", f_txt)
            ws.write_number(r, 3, ln["qty"], f_qty)
            if show_cost:
                ws.write_number(r, 4, ln.get("cost", 0), f_num)
            r += 1
            i += 1
        ws.write_string(r, 1, "JAMI", f_tot)
        ws.write_blank(r, 0, None, f_tot)
        ws.write_blank(r, 2, None, f_tot)
        ws.write_number(r, 3, d["total_qty"], f_tot)
        if show_cost:
            ws.write_number(r, 4, d.get("total_cost", 0), f_tot)
        wb.close()
        data = buf.getvalue()
        fname = "Otkazma_%s.xlsx" % str(
            d["in_name"] or picking_id).replace("/", "-")
        att = self.env["ir.attachment"].sudo().create({
            "name": fname, "type": "binary",
            "datas": base64.b64encode(data),
            "mimetype": ("application/vnd.openxmlformats-officedocument."
                         "spreadsheetml.sheet"),
        })
        return {"type": "ir.actions.act_url",
                "url": "/web/content/%d?download=true" % att.id,
                "target": "self"}

    # ================================================================== #
    #  7b · KAMOMAT — do'konga kam yetib borgan yuk                       #
    # ================================================================== #
    #  Manba: warehouse_transfer_custom_19v 1.5 qo'shgan maydonlar
    #      stock.move.feliza_kamomat            (bool, indeksli)
    #      stock.move.feliza_kamomat_shop_id    (qaysi do'konda kam chiqdi)
    #      stock.move.feliza_kamomat_delivery_id(asl jo'natma)
    #      stock.picking.feliza_kamomat_receipt_id (do'kon qabuli)
    #
    #  Kamomat "aniqlangan sana" — qaytarish hujjatining YARATILGAN sanasi
    #  (p.create_date): aynan do'kon «rezerv buyurtma kerak emas» bosgan
    #  payt. "Qaytarib olingan sana" — p.date_done.
    #
    #  Modul eski versiyada bo'lsa (maydon yo'q) — bo'lim bo'sh qaytadi.
    # ------------------------------------------------------------------ #
    @api.model
    def get_kamomat(self, period="month", date_from=None, date_to=None,
                    store=None):
        self._check_access_dashboard()
        if not self.env["feliza.detect"].has_kamomat():
            return {"available": False}

        d_from, d_to = self._period_dates(period, date_from, date_to)
        dt_from, dt_to = self._bounds(d_from, d_to)
        wh_ids = self._stock_warehouses(store).ids

        return {
            "available": True,
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "kpi": self._kam_kpi(wh_ids, dt_from, dt_to),
            "shops": self._kam_by_shop(wh_ids, dt_from, dt_to),
            "open_list": self._kam_open(wh_ids),
            "products": self._kam_products(wh_ids, dt_from, dt_to),
            "history": self._kam_history(wh_ids, dt_from, dt_to),
        }

    # ------------------------------------------------------------------ #
    # SQL matnlarida miqdor {QTY} deb yoziladi va `_kam_sql()` uni
    # bazadagi HAQIQIY holatga qarab almashtiradi (pastga qarang).
    _KAM_FROM = """
          FROM stock_move m
          JOIN stock_picking p ON p.id = m.picking_id
    """

    @api.model
    def _kam_sql(self, sql):
        """SQL matnidagi {QTY} ni miqdor ifodasiga almashtiradi.

        `feliza_kamomat_qty` (modul 1.6) — do'kon qabulni tasdiqlagan
        paytdagi ANIQ kamomat: skladchi keyin bir qismini qabul qilsa
        ham o'zgarmaydi. Modul 1.5 bo'lsa bu USTUN bazada umuman yo'q —
        o'shanda `product_uom_qty` ishlatiladi. Shu tekshiruvsiz
        dashboard "column ... does not exist" deb yiqilardi.
        """
        if self.env["feliza.detect"].has_kamomat_qty():
            miqdor = ("COALESCE(NULLIF(m.feliza_kamomat_qty, 0),"
                      " m.product_uom_qty)")
        else:
            miqdor = "m.product_uom_qty"
        return sql.replace("{QTY}", miqdor)

    @api.model
    def _kam_where(self, wh_ids):
        """Ruxsat etilgan omborlar: qaytarishni oluvchi sklad YOKI do'kon."""
        if not wh_ids:
            return " AND FALSE", []
        return (" AND m.feliza_kamomat = TRUE AND m.state <> 'cancel'"
                " AND (p.warehouse_id = ANY(%s)"
                "   OR m.feliza_kamomat_shop_id = ANY(%s))"), [wh_ids, wh_ids]

    @api.model
    def _kam_cost_sql(self):
        """Tannarx ustuni — FAQAT rahbar uchun, aks holda nol."""
        if not self._show_cost():
            return "0", []
        return ("COALESCE(SUM({QTY}"
                " * COALESCE((pp.standard_price ->> %s)::numeric, 0)), 0)",
                [str(self.env.company.id)])

    @api.model
    def _kam_kpi(self, wh_ids, dt_from, dt_to):
        show_cost = self._show_cost()
        empty = {"open_qty": 0.0, "open_docs": 0, "open_lines": 0,
                 "open_days": 0.0, "old_docs": 0,
                 "period_qty": 0.0, "period_docs": 0, "period_shops": 0,
                 "done_qty": 0.0, "open_cost": 0.0, "period_cost": 0.0}
        if not wh_ids:
            return empty
        cond, params = self._kam_where(wh_ids)
        cost_sql, cost_params = self._kam_cost_sql()
        join_p = (" JOIN product_product pp ON pp.id = m.product_id"
                  if show_cost else "")

        # 1) HOZIR qaytarilmagan (davrga bog'liq emas — joriy holat)
        self.env.cr.execute(self._kam_sql("""
            SELECT COALESCE(SUM({QTY}), 0),
                   COUNT(DISTINCT m.picking_id),
                   COUNT(*),
                   COALESCE(AVG(EXTRACT(EPOCH FROM (now() - p.create_date))
                                / 86400.0), 0),
                   COUNT(DISTINCT m.picking_id)
                     FILTER (WHERE p.create_date < now() - interval '3 days'),
                   """ + cost_sql + """
        """ + self._KAM_FROM + join_p + """
             WHERE p.state NOT IN ('done', 'cancel')
        """ + cond), cost_params + params)
        o = self.env.cr.fetchone() or (0, 0, 0, 0, 0, 0)

        # 2) DAVRDA aniqlangan kamomat
        self.env.cr.execute(self._kam_sql("""
            SELECT COALESCE(SUM({QTY}), 0),
                   COUNT(DISTINCT m.picking_id),
                   COUNT(DISTINCT m.feliza_kamomat_shop_id),
                   COALESCE(SUM({QTY})
                            FILTER (WHERE p.state = 'done'), 0),
                   """ + cost_sql + """
        """ + self._KAM_FROM + join_p + """
             WHERE p.create_date >= %s AND p.create_date <= %s
        """ + cond), cost_params + [dt_from, dt_to] + params)
        d = self.env.cr.fetchone() or (0, 0, 0, 0, 0)

        res = {
            "open_qty": float(o[0] or 0),
            "open_docs": int(o[1] or 0),
            "open_lines": int(o[2] or 0),
            "open_days": float(o[3] or 0),
            "old_docs": int(o[4] or 0),
            "period_qty": float(d[0] or 0),
            "period_docs": int(d[1] or 0),
            "period_shops": int(d[2] or 0),
            "done_qty": float(d[3] or 0),
        }
        if show_cost:
            res["open_cost"] = float(o[5] or 0)
            res["period_cost"] = float(d[4] or 0)
        return res

    @api.model
    def _kam_by_shop(self, wh_ids, dt_from, dt_to):
        """Do'kon kesimi: davrda qancha kamomat, hozir qanchasi qaytmagan."""
        if not wh_ids:
            return []
        cond, params = self._kam_where(wh_ids)
        show_cost = self._show_cost()
        cost_sql, cost_params = self._kam_cost_sql()
        join_p = (" JOIN product_product pp ON pp.id = m.product_id"
                  if show_cost else "")

        self.env.cr.execute(self._kam_sql("""
            SELECT m.feliza_kamomat_shop_id,
                   COALESCE(SUM({QTY}), 0)                AS qty,
                   COUNT(DISTINCT m.picking_id)                       AS docs,
                   COALESCE(SUM({QTY})
                            FILTER (WHERE p.state NOT IN ('done','cancel')), 0)
                                                                      AS ochiq,
                   COALESCE(SUM({QTY})
                            FILTER (WHERE p.state = 'done'), 0)       AS qaytdi,
                   COUNT(DISTINCT m.feliza_kamomat_delivery_id)       AS jonatma,
                   """ + cost_sql + """                               AS cost
        """ + self._KAM_FROM + join_p + """
             WHERE p.create_date >= %s AND p.create_date <= %s
        """ + cond + """
             GROUP BY 1
             ORDER BY qty DESC
        """), cost_params + [dt_from, dt_to] + params)
        rows = self.env.cr.fetchall()
        if not rows:
            return []

        whs = self.env["stock.warehouse"].sudo().browse(
            [r[0] for r in rows if r[0]])
        wname = {w.id: w.name for w in whs}
        out = []
        for r in rows:
            item = {
                "id": r[0] or 0,
                "name": wname.get(r[0], "—"),
                "qty": float(r[1] or 0),
                "docs": int(r[2] or 0),
                "open": float(r[3] or 0),
                "done": float(r[4] or 0),
                "deliveries": int(r[5] or 0),
            }
            if show_cost:
                item["cost"] = float(r[6] or 0)
            out.append(item)
        return out

    @api.model
    def _kam_open(self, wh_ids, limit=50):
        """Hozir skladga qaytarilmagan hujjatlar — eng eskisi yuqorida."""
        if not wh_ids:
            return []
        cond, params = self._kam_where(wh_ids)
        show_cost = self._show_cost()
        cost_sql, cost_params = self._kam_cost_sql()
        join_p = (" JOIN product_product pp ON pp.id = m.product_id"
                  if show_cost else "")

        self.env.cr.execute(self._kam_sql("""
            SELECT m.picking_id,
                   MIN(p.create_date)                    AS aniqlandi,
                   COALESCE(SUM({QTY}), 0)   AS qty,
                   COUNT(*)                              AS lines,
                   MIN(p.warehouse_id)                   AS sklad,
                   MIN(m.feliza_kamomat_shop_id)         AS dokon,
                   MIN(m.feliza_kamomat_delivery_id)     AS jonatma,
                   MIN(p.feliza_kamomat_receipt_id)      AS qabul,
                   """ + cost_sql + """                  AS cost
        """ + self._KAM_FROM + join_p + """
             WHERE p.state NOT IN ('done', 'cancel')
        """ + cond + """
             GROUP BY m.picking_id
             ORDER BY aniqlandi ASC
             LIMIT %s
        """), cost_params + params + [limit])
        rows = self.env.cr.fetchall()
        if not rows:
            return []
        return self._kam_doc_rows(rows, show_cost, sana_ustun=1)

    @api.model
    def _kam_history(self, wh_ids, dt_from, dt_to, limit=200):
        """Davrda aniqlangan BARCHA kamomat — hujjat kesimida."""
        if not wh_ids:
            return []
        cond, params = self._kam_where(wh_ids)
        show_cost = self._show_cost()
        cost_sql, cost_params = self._kam_cost_sql()
        join_p = (" JOIN product_product pp ON pp.id = m.product_id"
                  if show_cost else "")

        self.env.cr.execute(self._kam_sql("""
            SELECT m.picking_id,
                   MIN(p.create_date)                    AS aniqlandi,
                   COALESCE(SUM({QTY}), 0)   AS qty,
                   COUNT(*)                              AS lines,
                   MIN(p.warehouse_id)                   AS sklad,
                   MIN(m.feliza_kamomat_shop_id)         AS dokon,
                   MIN(m.feliza_kamomat_delivery_id)     AS jonatma,
                   MIN(p.feliza_kamomat_receipt_id)      AS qabul,
                   """ + cost_sql + """                  AS cost,
                   MIN(p.state)                          AS holat,
                   MAX(p.date_done)                      AS qaytdi
        """ + self._KAM_FROM + join_p + """
             WHERE p.create_date >= %s AND p.create_date <= %s
        """ + cond + """
             GROUP BY m.picking_id
             ORDER BY aniqlandi DESC
             LIMIT %s
        """), cost_params + [dt_from, dt_to] + params + [limit])
        rows = self.env.cr.fetchall()
        if not rows:
            return []
        return self._kam_doc_rows(rows, show_cost, sana_ustun=1, holat=True)

    @api.model
    def _kam_doc_rows(self, rows, show_cost, sana_ustun=1, holat=False):
        """SQL qatorlarini ekran uchun tayyorlaydi (nomlar bitta so'rovda)."""
        Picking = self.env["stock.picking"].sudo()
        pid = set()
        for r in rows:
            pid |= {r[0], r[6], r[7]}
        pnames = {p.id: p.name for p in Picking.browse([i for i in pid if i])}
        wid = {r[4] for r in rows} | {r[5] for r in rows}
        wname = {w.id: w.name for w in
                 self.env["stock.warehouse"].sudo().browse(
                     [i for i in wid if i])}
        tz = self._tz()
        hozir = datetime.now()

        out = []
        for r in rows:
            dt = r[sana_ustun]
            local = pytz.UTC.localize(dt).astimezone(tz) if dt else None
            item = {
                "id": r[0],
                "name": pnames.get(r[0], "?"),
                "date": local.strftime("%d.%m.%Y %H:%M") if local else "",
                "days": (hozir - dt).days if dt else 0,
                "qty": float(r[2] or 0),
                "lines": int(r[3] or 0),
                "warehouse": wname.get(r[4], "—"),
                "shop": wname.get(r[5], "—"),
                "delivery": pnames.get(r[6], "—"),
                "delivery_id": r[6] or 0,
                "receipt": pnames.get(r[7], "—"),
                "receipt_id": r[7] or 0,
            }
            if show_cost:
                item["cost"] = float(r[8] or 0)
            if holat:
                item["state"] = r[9] or ""
                item["done"] = r[9] == "done"
                dd = r[10]
                dl = pytz.UTC.localize(dd).astimezone(tz) if dd else None
                item["done_date"] = dl.strftime("%d.%m.%Y %H:%M") if dl else ""
            out.append(item)
        return out

    @api.model
    def _kam_products(self, wh_ids, dt_from, dt_to, limit=20):
        """Davrda eng ko'p kamomat chiqqan tovarlar."""
        if not wh_ids:
            return []
        cond, params = self._kam_where(wh_ids)
        show_cost = self._show_cost()
        cost_sql, cost_params = self._kam_cost_sql()
        join_p = (" JOIN product_product pp ON pp.id = m.product_id"
                  if show_cost else "")

        self.env.cr.execute(self._kam_sql("""
            SELECT m.product_id,
                   COALESCE(SUM({QTY}), 0)          AS qty,
                   COUNT(DISTINCT m.picking_id)                 AS docs,
                   COUNT(DISTINCT m.feliza_kamomat_shop_id)     AS shops,
                   """ + cost_sql + """                         AS cost
        """ + self._KAM_FROM + join_p + """
             WHERE p.create_date >= %s AND p.create_date <= %s
        """ + cond + """
             GROUP BY 1
             ORDER BY qty DESC
             LIMIT %s
        """), cost_params + [dt_from, dt_to] + params + [limit])
        rows = self.env.cr.fetchall()
        if not rows:
            return []

        by_id = {p.id: p for p in
                 self.env["product.product"].sudo().browse([r[0] for r in rows])}
        out = []
        for r in rows:
            p = by_id.get(r[0])
            item = {
                "id": r[0],
                "name": p.display_name if p else "?",
                "code": (p.default_code or "") if p else "",
                "qty": float(r[1] or 0),
                "docs": int(r[2] or 0),
                "shops": int(r[3] or 0),
            }
            if show_cost:
                item["cost"] = float(r[4] or 0)
            out.append(item)
        return out

    # ================================================================== #
    #  8 · ICHIGA KIRISH (drill-down)                                     #
    # ================================================================== #
    #  Frontend faqat "nimani ochish" kerakligini aytadi, DOMEN va
    #  huquq tekshiruvi shu yerda — serverda hal qilinadi.
    # ------------------------------------------------------------------ #
    @api.model
    def open_view(self, kind, rec_id=None, period=None, date_from=None,
                  date_to=None, store=None, model=None):
        self._check_access_dashboard()
        configs = self._scoped_configs(store)
        d_from, d_to = self._period_dates(period or "today", date_from, date_to)
        dt_from, dt_to = self._bounds(d_from, d_to)

        def act(name, model, domain=None, res_id=None, views=None):
            action = {
                "type": "ir.actions.act_window",
                "name": name,
                "res_model": model,
                "target": "current",
                "context": {},
            }
            if res_id:
                action["res_id"] = res_id
                action["views"] = [(False, "form")]
            else:
                action["domain"] = domain or []
                action["views"] = views or [(False, "list"), (False, "form")]
            return action

        # --- xodim ---
        if kind == "employee":
            allowed = ("hr.employee", "res.users", "res.partner")
            if model not in allowed:
                info = self.env["feliza.detect"].salesperson_info()
                model = (info or {}).get("comodel") or "res.users"
            if model not in allowed or model not in self.env:
                raise AccessError(_("Yozuv topilmadi."))
            if not self.env[model].sudo().browse(int(rec_id)).exists():
                raise AccessError(_("Yozuv topilmadi."))
            return act(_("Xodim"), model, res_id=int(rec_id))

        # --- tovar ---
        if kind == "product":
            return act(_("Mahsulot"), "product.product", res_id=int(rec_id))

        # --- bitta chek (Odoo formasi) ---
        if kind in ("order", "order_form"):
            order = self.env["pos.order"].sudo().browse(int(rec_id))
            if not order.exists() or order.config_id.id not in configs.ids:
                raise AccessError(_("Bu chekni ko'rish huquqi yo'q."))
            return act(_("Chek"), "pos.order", res_id=int(rec_id))

        # --- do'kon cheklari (davr bo'yicha) ---
        if kind == "store_orders":
            cfgs = self._scoped_configs(rec_id or store)
            return act(
                _("Cheklar — %s", rec_id or _("barcha do'konlar")),
                "pos.order",
                domain=[("config_id", "in", cfgs.ids),
                        ("state", "in", list(POS_DONE_STATES)),
                        ("date_order", ">=", fields.Datetime.to_string(dt_from)),
                        ("date_order", "<=", fields.Datetime.to_string(dt_to))],
            )

        # --- chegirmali cheklar ---
        if kind == "discount_orders":
            cfgs = self._scoped_configs(rec_id or store)
            self.env.cr.execute("""
                SELECT DISTINCT o.id FROM pos_order o
                  JOIN pos_order_line l ON l.order_id = o.id
                 WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
                   AND o.date_order >= %s AND o.date_order <= %s
                   AND l.discount > 0
            """, (cfgs.ids, list(POS_DONE_STATES), dt_from, dt_to))
            ids = [r[0] for r in self.env.cr.fetchall()]
            return act(_("Chegirmali cheklar"), "pos.order",
                       domain=[("id", "in", ids)])

        # --- ombordagi qoldiq ---
        if kind == "warehouse_stock":
            whs = self._stock_warehouses()
            wh = whs.filtered(lambda w: w.id == int(rec_id))
            if not wh:
                raise AccessError(_("Bu omborni ko'rish huquqi yo'q."))
            locs = self.env["stock.location"].sudo().search([
                ("id", "child_of", wh.view_location_id.id),
                ("usage", "=", "internal")])
            return act(_("Qoldiq — %s", wh.name), "stock.quant",
                       domain=[("location_id", "in", locs.ids),
                               ("quantity", "!=", 0)])

        # --- o'tkazma hujjati ---
        if kind == "picking":
            return act(_("O'tkazma"), "stock.picking", res_id=int(rec_id))

        # --- zakup hujjati (zakupchi paneli) ---
        if kind == "purchase":
            self._check_zakup_access()
            return act(_("Zakup"), "purchase.order", res_id=int(rec_id))

        # --- kamomat: barcha qatorlar / faqat qaytarilmaganlar ---
        if kind in ("kamomat_moves", "kamomat_open", "kamomat_shop"):
            if not self.env["feliza.detect"].has_kamomat():
                raise AccessError(_("Kamomat bo'limi mavjud emas."))
            whs = self._stock_warehouses(store)
            # ro'yxatdagi har bir band VA bilan birikadi; oxirgi uchlik esa
            # "qaytarib oluvchi sklad YOKI kamomat chiqqan do'kon" degani
            qamrov = [("feliza_kamomat", "=", True),
                      "|", ("picking_id.warehouse_id", "in", whs.ids),
                           ("feliza_kamomat_shop_id", "in", whs.ids)]
            if kind == "kamomat_open":
                nom = _("Kamomat — qaytarilmagan")
                dom = [("state", "not in", ("done", "cancel"))] + qamrov
            elif kind == "kamomat_shop":
                shop = whs.filtered(lambda w: w.id == int(rec_id or 0))
                if not shop:
                    raise AccessError(_("Bu omborni ko'rish huquqi yo'q."))
                nom = _("Kamomat — %s", shop.name)
                dom = [("feliza_kamomat_shop_id", "=", shop.id)] + qamrov
            else:
                nom = _("Kamomat")
                dom = [("picking_id.create_date", ">=",
                        fields.Datetime.to_string(dt_from)),
                       ("picking_id.create_date", "<=",
                        fields.Datetime.to_string(dt_to))] + qamrov
            # Modulning O'ZINING chiroyli kamomat ko'rinishlari bilan
            # ochamiz — standart stock.move ro'yxati kerakli ustunlarni
            # (jo'natma, do'kon, qabul hujjati) ko'rsatmaydi.
            def _v(xmlid):
                return self.env["ir.model.data"]._xmlid_to_res_id(
                    "warehouse_transfer_custom_19v." + xmlid,
                    raise_if_not_found=False) or False

            action = act(nom, "stock.move", domain=dom)
            action["views"] = [(_v("view_kamomat_move_list"), "list"),
                               (_v("view_kamomat_move_pivot"), "pivot"),
                               (_v("view_kamomat_move_graph"), "graph")]
            qidiruv = _v("view_kamomat_move_search")
            if qidiruv:
                action["search_view_id"] = [qidiruv, "search"]
            return action

        # --- yo'ldagi o'tkazmalar ro'yxati ---
        if kind == "transit_moves":
            whs = self._stock_warehouses(store)
            return act(_("Yo'ldagi o'tkazmalar"), "stock.move",
                       domain=["&", ("interwh_report_status", "=", "in_transit"),
                               "|", ("real_source_warehouse_id", "in", whs.ids),
                                    ("real_dest_warehouse_id", "in", whs.ids)])

        raise AccessError(_("Noma'lum bo'lim: %s", kind))

    # ================================================================== #
    #  9 · CHEK KARTASI (dashboard ichida ochiladi)                       #
    # ================================================================== #
    #  Odoo'ning pos.order formasini ochish uchun foydalanuvchida POS
    #  huquqi bo'lishi kerak. Do'kon boshlig'ida u bo'lmasligi mumkin —
    #  shuning uchun chek ma'lumoti shu yerda tayyorlanadi va panel
    #  ichidagi oynada ko'rsatiladi. Qamrov tekshiruvi baribir bor.
    # ------------------------------------------------------------------ #
    @api.model
    def get_order_detail(self, order_id):
        self._check_access_dashboard()
        configs = self._allowed_configs()
        order = self.env["pos.order"].sudo().browse(int(order_id))
        if not order.exists() or order.config_id.id not in configs.ids:
            raise AccessError(_("Bu chekni ko'rish huquqi yo'q."))

        show_cost = self._show_cost()
        tz = self._tz()
        local = pytz.UTC.localize(order.date_order).astimezone(tz) \
            if order.date_order else None

        info = self.env["feliza.detect"].salesperson_info()
        seller = ""
        if info:
            rec = order[info["field"]] if not info.get("on_line") \
                and info["field"] in order._fields else None
            if rec:
                seller = rec.display_name

        lines = []
        gross = disc_total = cost_total = 0.0
        for l in order.lines:
            line_gross = (l.price_unit or 0.0) * (l.qty or 0.0)
            line_disc = line_gross * (l.discount or 0.0) / 100.0
            gross += line_gross
            disc_total += line_disc
            item = {
                "id": l.product_id.id,
                "name": l.full_product_name or l.product_id.display_name,
                "code": l.product_id.default_code or "",
                "qty": l.qty,
                "price": l.price_unit,
                "discount": l.discount,
                "discount_amount": line_disc,
                "subtotal": l.price_subtotal_incl,
            }
            if show_cost:
                c = (l.product_id.standard_price or 0.0) * (l.qty or 0.0)
                cost_total += c
                item["cost"] = c
                item["margin"] = ((l.price_subtotal_incl - c) / l.price_subtotal_incl
                                  * 100.0) if l.price_subtotal_incl else 0.0
            lines.append(item)

        payments = [{
            "name": p.payment_method_id.name,
            "amount": p.amount,
            "is_cash": bool(p.payment_method_id.is_cash_count),
        } for p in order.payment_ids]

        data = {
            "id": order.id,
            "ref": order.pos_reference or order.name,
            "name": order.name,
            "date": local.strftime("%d.%m.%Y %H:%M") if local else "",
            "store": (order.config_id.feliza_store_group or "").strip()
                     or order.config_id.name,
            "cashier": order.user_id.display_name or "",
            "seller": seller,
            "partner": order.partner_id.display_name or "",
            "state": order.state,
            "session": order.session_id.name,
            "lines": lines,
            "payments": payments,
            "gross": gross,
            "discount": disc_total,
            "total": order.amount_total,
            "units": sum(l.qty for l in order.lines),
        }
        if show_cost:
            data["cost"] = cost_total
            data["profit"] = order.amount_total - cost_total
            data["margin"] = ((order.amount_total - cost_total)
                              / order.amount_total * 100.0) if order.amount_total else 0.0
        return data

    # ================================================================== #
    #  10 · TO'LOV TURI TAFSILOTI                                         #
    # ================================================================== #
    @api.model
    def get_payment_detail(self, method_id, period="today", date_from=None,
                           date_to=None, store=None):
        self._check_access_dashboard()
        configs = self._scoped_configs(store)
        d_from, d_to = self._period_dates(period, date_from, date_to)
        dt_from, dt_to = self._bounds(d_from, d_to)
        PM = self.env["pos.payment.method"].sudo()
        if isinstance(method_id, str) and not method_id.isdigit():
            # nom bo'yicha — barcha do'konlardagi bir xil nomli usullar
            key = method_id.strip().lower()
            methods = PM.search([]).filtered(
                lambda m: (m.name or "").strip().lower() == key)
            title = method_id.strip()
        else:
            methods = PM.browse(int(method_id))
            title = methods.name if methods else "?"
        if not methods:
            return {"id": 0, "name": title, "is_cash": False,
                    "period": {"from": str(d_from), "to": str(d_to)},
                    "total": 0.0, "count": 0, "orders": 0, "avg": 0.0,
                    "min": 0.0, "max": 0.0, "stores": [], "cashiers": [],
                    "daily": [], "max_daily": 0.0, "methods": []}

        base = """
              FROM pos_payment p
              JOIN pos_order o ON o.id = p.pos_order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
               AND p.payment_method_id = ANY(%s)
        """
        params = (configs.ids, list(POS_DONE_STATES), dt_from, dt_to, methods.ids)

        # umumiy
        self.env.cr.execute("""
            SELECT COALESCE(SUM(p.amount), 0), COUNT(*), COUNT(DISTINCT o.id),
                   COALESCE(MIN(p.amount), 0), COALESCE(MAX(p.amount), 0)
        """ + base, params)
        t = self.env.cr.fetchone() or (0, 0, 0, 0, 0)

        # do'kon bo'yicha
        self.env.cr.execute("""
            SELECT o.config_id, SUM(p.amount), COUNT(*)
        """ + base + " GROUP BY 1 ORDER BY 2 DESC", params)
        cfg_rows = self.env.cr.fetchall()
        cfgs = self.env["pos.config"].sudo().browse([r[0] for r in cfg_rows])
        cname = {c.id: ((c.feliza_store_group or "").strip() or c.name) for c in cfgs}
        by_store = {}
        for cid, amount, cnt in cfg_rows:
            key = cname.get(cid, "?")
            slot = by_store.setdefault(key, {"store": key, "amount": 0.0, "count": 0})
            slot["amount"] += float(amount or 0)
            slot["count"] += int(cnt or 0)
        stores = sorted(by_store.values(), key=lambda x: -x["amount"])

        # kassir bo'yicha
        self.env.cr.execute("""
            SELECT o.user_id, SUM(p.amount), COUNT(*)
        """ + base + " GROUP BY 1 ORDER BY 2 DESC LIMIT 20", params)
        user_rows = self.env.cr.fetchall()
        users = self.env["res.users"].sudo().browse([r[0] for r in user_rows if r[0]])
        uname = {u.id: u.display_name for u in users}
        cashiers = [{
            "id": r[0], "name": uname.get(r[0], "?"),
            "amount": float(r[1] or 0), "count": int(r[2] or 0),
        } for r in user_rows if r[0]]

        # kunlik dinamika
        tz_name = self.env.user.tz or "Asia/Tashkent"
        self.env.cr.execute("""
            SELECT (o.date_order AT TIME ZONE 'UTC' AT TIME ZONE %s)::date AS d,
                   SUM(p.amount)
              FROM pos_payment p
              JOIN pos_order o ON o.id = p.pos_order_id
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
               AND p.payment_method_id = ANY(%s)
             GROUP BY 1 ORDER BY 1
        """, (tz_name,) + tuple(params))
        daily = [{"date": str(r[0]), "amount": float(r[1] or 0)}
                 for r in self.env.cr.fetchall()]

        count = int(t[1] or 0)
        total = float(t[0] or 0)
        return {
            "id": methods[:1].id,
            "name": title,
            "is_cash": any(m.is_cash_count for m in methods),
            "methods": len(methods),
            "period": {"from": str(d_from), "to": str(d_to)},
            "total": total,
            "count": count,
            "orders": int(t[2] or 0),
            "avg": total / count if count else 0.0,
            "min": float(t[3] or 0),
            "max": float(t[4] or 0),
            "stores": stores,
            "cashiers": cashiers,
            "daily": daily,
            "max_daily": max([d["amount"] for d in daily], default=0.0),
        }

    # ================================================================== #
    #  11 · TREND (sparkline uchun) VA SOATLIK TAQQOSLASH                 #
    # ================================================================== #
    @api.model
    def _trend(self, configs, days=14):
        """So'nggi N kunning kunlik ko'rsatkichlari — mini grafik uchun."""
        if not configs:
            return []
        d_to = self._today()
        d_from = d_to - timedelta(days=days - 1)
        dt_from, dt_to = self._bounds(d_from, d_to)
        tz_name = self.env.user.tz or "Asia/Tashkent"

        self.env.cr.execute("""
            SELECT (o.date_order AT TIME ZONE 'UTC' AT TIME ZONE %s)::date AS d,
                   SUM(o.amount_total)                       AS revenue,
                   COUNT(*)                                  AS orders,
                   COALESCE(SUM(li.qty), 0)                  AS units,
                   COALESCE(SUM(li.disc), 0)                 AS discount
              FROM pos_order o
              LEFT JOIN LATERAL (
                   SELECT SUM(l.qty) AS qty,
                          SUM(l.price_unit * l.qty * l.discount / 100.0) AS disc
                     FROM pos_order_line l WHERE l.order_id = o.id
              ) li ON TRUE
             WHERE o.config_id = ANY(%s) AND o.state = ANY(%s)
               AND o.date_order >= %s AND o.date_order <= %s
             GROUP BY 1 ORDER BY 1
        """, (tz_name, configs.ids, list(POS_DONE_STATES), dt_from, dt_to))

        found = {r[0]: r for r in self.env.cr.fetchall()}
        out = []
        for i in range(days):
            d = d_from + timedelta(days=i)
            r = found.get(d)
            rev = float(r[1] or 0) if r else 0.0
            cnt = int(r[2] or 0) if r else 0
            units = float(r[3] or 0) if r else 0.0
            disc = float(r[4] or 0) if r else 0.0
            out.append({
                "date": str(d),
                "revenue": rev,
                "orders": cnt,
                "avg_check": rev / cnt if cnt else 0.0,
                "upt": units / cnt if cnt else 0.0,
                "discount_pct": disc / (rev + disc) * 100.0 if (rev + disc) else 0.0,
            })
        return out

    # ================================================================== #
    #  12 · MOLIYA — BALANS VA FOYDA/ZARAR (P&L)                          #
    # ================================================================== #
    #  Manba: account.move.line (faqat parent_state = 'posted').
    #  Balans   = debit − credit (sana boshidan hozirgacha, to'plangan)
    #  P&L      = tanlangan davr ichidagi daromad va xarajatlar
    #
    #  MUHIM: bu bo'lim FAQAT rahbar uchun. Do'kon boshlig'iga umuman
    #  ochilmaydi (AccessError).
    # ------------------------------------------------------------------ #
    BS_GROUPS = [
        ("cash", "Kassa va bank", ("asset_cash",), "asset"),
        ("receivable", "Debitorlik (bizdan qarz)", ("asset_receivable",), "asset"),
        ("current", "Boshqa joriy aktivlar", ("asset_current", "asset_prepayments"), "asset"),
        ("fixed", "Asosiy vositalar", ("asset_fixed", "asset_non_current"), "asset"),
        ("payable", "Kreditorlik (biz qarzdormiz)", ("liability_payable",), "liability"),
        ("credit_card", "Kredit kartalar", ("liability_credit_card",), "liability"),
        ("liab", "Boshqa majburiyatlar",
         ("liability_current", "liability_non_current"), "liability"),
        ("equity", "Kapital", ("equity", "equity_unaffected"), "equity"),
    ]

    PL_GROUPS = [
        ("income", "Sotuvdan daromad", ("income",), 1),
        ("income_other", "Boshqa daromad", ("income_other",), 1),
        ("cogs", "Sotilgan tovar tannarxi", ("expense_direct_cost",), -1),
        ("expense", "Xarajatlar", ("expense", "expense_depreciation"), -1),
    ]

    #  Yangi/nostandart hisob turlari uchun zaxira qoida — hech qanday
    #  summa hisobdan tushib qolmasligi uchun (balans har doim tenglashadi).
    @api.model
    def _side_of(self, account_type):
        if account_type.startswith("asset"):
            return "asset"
        if account_type.startswith("liability"):
            return "liability"
        if account_type.startswith("equity"):
            return "equity"
        return "pnl"

    @api.model
    def _check_finance(self):
        self._check_access_dashboard()
        if not self._is_manager():
            raise AccessError(_("Moliya bo'limi faqat rahbar uchun."))

    @api.model
    def get_finance(self, period="month", date_from=None, date_to=None, store=None):
        self._check_finance()
        d_from, d_to = self._period_dates(period, date_from, date_to)
        companies = self.env.companies.ids

        balance = self._balance_sheet(companies, d_to)
        pnl = self._profit_loss(companies, d_from, d_to)
        by_key = {g["key"]: g["amount"] for g in balance["groups"]}

        return {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "company": self.env.company.name,
            "balance": balance,
            "pnl": pnl,
            "accounts": self._top_accounts(companies, d_to),
            "cash_flow": self._cash_flow(companies, d_from, d_to),
            "unposted": self._unposted_count(companies),
            "kpi": {
                "cash": by_key.get("cash", 0.0),
                "receivable": by_key.get("receivable", 0.0),
                "payable": by_key.get("payable", 0.0),
                "net_assets": balance["assets"] - balance["liabilities"],
            },
        }

    @api.model
    def _balance_sheet(self, companies, date_to):
        """Balans — sana holatiga to'plangan qoldiq."""
        self.env.cr.execute("""
            SELECT a.account_type, SUM(l.balance) AS bal, COUNT(*) AS lines
              FROM account_move_line l
              JOIN account_account a ON a.id = l.account_id
             WHERE l.parent_state = 'posted'
               AND l.company_id = ANY(%s)
               AND l.date <= %s
             GROUP BY 1
        """, (companies, date_to))
        by_type = {r[0]: {"bal": float(r[1] or 0), "lines": int(r[2] or 0)}
                   for r in self.env.cr.fetchall()}

        known = {t for _k, _l, tps, _s in self.BS_GROUPS for t in tps}
        known |= {t for _k, _l, tps, _sg in self.PL_GROUPS for t in tps}
        extra = [t for t in by_type if t not in known]

        groups = []
        totals = {"asset": 0.0, "liability": 0.0, "equity": 0.0}
        bs_groups = list(self.BS_GROUPS)
        for t in extra:
            side = self._side_of(t)
            if side != "pnl":
                bs_groups.append(("extra_" + t, _("Boshqa — %s", t), (t,), side))

        for key, label, types, side in bs_groups:
            bal = sum(by_type.get(t, {}).get("bal", 0.0) for t in types)
            lines = sum(by_type.get(t, {}).get("lines", 0) for t in types)
            # passiv va kapital hisoblarida qoldiq manfiy bo'ladi (kredit),
            # foydalanuvchiga musbat ko'rinishi kerak
            shown = bal if side == "asset" else -bal
            totals[side] += shown
            groups.append({
                "key": key, "label": label, "side": side,
                "side_label": {"asset": _("aktiv"),
                               "liability": _("majburiyat"),
                               "equity": _("kapital")}[side],
                "amount": shown, "lines": lines, "types": list(types),
            })

        # davr foydasi (yopilmagan) — daromad − xarajat
        self.env.cr.execute("""
            SELECT SUM(l.balance)
              FROM account_move_line l
              JOIN account_account a ON a.id = l.account_id
             WHERE l.parent_state = 'posted'
               AND l.company_id = ANY(%s) AND l.date <= %s
               AND (a.account_type LIKE 'income%%' OR a.account_type LIKE 'expense%%')
        """, (companies, date_to))
        result = float((self.env.cr.fetchone() or [0])[0] or 0)
        profit = -result   # daromad kredit → manfiy balans

        passive_total = totals["liability"] + totals["equity"] + profit
        diff = totals["asset"] - passive_total
        return {
            "groups": groups,
            "assets": totals["asset"],
            "liabilities": totals["liability"],
            "equity": totals["equity"],
            "profit": profit,
            "passive_total": passive_total,
            # tekshiruv: aktiv = passiv + kapital + davr foydasi
            "check_diff": diff,
            "is_balanced": abs(diff) < 1.0,
        }

    @api.model
    def _profit_loss(self, companies, date_from, date_to):
        """Foyda va zarar — davr ichida."""
        self.env.cr.execute("""
            SELECT a.account_type, SUM(l.balance), COUNT(*)
              FROM account_move_line l
              JOIN account_account a ON a.id = l.account_id
             WHERE l.parent_state = 'posted'
               AND l.company_id = ANY(%s)
               AND l.date >= %s AND l.date <= %s
               AND (a.account_type LIKE 'income%%' OR a.account_type LIKE 'expense%%')
             GROUP BY 1
        """, (companies, date_from, date_to))
        by_type = {r[0]: (float(r[1] or 0), int(r[2] or 0))
                   for r in self.env.cr.fetchall()}

        known = {t for _k, _l, tps, _s in self.PL_GROUPS for t in tps}
        pl_groups = list(self.PL_GROUPS)
        for t in by_type:
            if t not in known:
                pl_groups.append(("extra_" + t, _("Boshqa — %s", t), (t,),
                                  1 if t.startswith("income") else -1))

        rows = []
        income = cogs = expense = 0.0
        for key, label, types, sign in pl_groups:
            bal = sum(by_type.get(t, (0.0, 0))[0] for t in types)
            lines = sum(by_type.get(t, (0.0, 0))[1] for t in types)
            amount = -bal if sign > 0 else bal   # daromad kredit, xarajat debet
            if key.startswith("income"):
                income += amount
            elif key == "cogs":
                cogs += amount
            else:
                expense += amount
            rows.append({"key": key, "label": label, "amount": amount,
                         "lines": lines, "types": list(types), "sign": sign})

        gross = income - cogs
        net = income - cogs - expense
        return {
            "rows": rows,
            "income": income,
            "cogs": cogs,
            "gross": gross,
            "gross_pct": gross / income * 100.0 if income else 0.0,
            "expense": expense,
            "net": net,
            "net_pct": net / income * 100.0 if income else 0.0,
        }

    @api.model
    def _top_accounts(self, companies, date_to, limit=25):
        """Eng katta qoldiqli hisoblar."""
        self.env.cr.execute("""
            SELECT a.id, a.code_store->>'1', a.name->>'en_US', a.account_type,
                   SUM(l.balance) AS bal, COUNT(*) AS lines
              FROM account_move_line l
              JOIN account_account a ON a.id = l.account_id
             WHERE l.parent_state = 'posted'
               AND l.company_id = ANY(%s) AND l.date <= %s
             GROUP BY 1, 2, 3, 4
            HAVING ABS(SUM(l.balance)) > 0.01
             ORDER BY ABS(SUM(l.balance)) DESC
             LIMIT %s
        """, (companies, date_to, limit))
        rows = self.env.cr.fetchall()
        accounts = self.env["account.account"].sudo().browse([r[0] for r in rows])
        code = {a.id: (a.code or "") for a in accounts}
        name = {a.id: a.display_name for a in accounts}
        labels = {
            "asset_cash": _("kassa/bank"), "asset_receivable": _("debitorlik"),
            "asset_current": _("joriy aktiv"), "asset_prepayments": _("avans"),
            "asset_fixed": _("asosiy vosita"), "asset_non_current": _("uzoq muddatli"),
            "liability_payable": _("kreditorlik"),
            "liability_credit_card": _("kredit karta"),
            "liability_current": _("joriy majburiyat"),
            "liability_non_current": _("uzoq majburiyat"),
            "equity": _("kapital"), "equity_unaffected": _("o'tgan yil foydasi"),
            "income": _("daromad"), "income_other": _("boshqa daromad"),
            "expense": _("xarajat"), "expense_direct_cost": _("tovar tannarxi"),
        }
        return [{
            "id": r[0],
            "code": code.get(r[0]) or (r[1] or ""),
            "name": name.get(r[0]) or (r[2] or ""),
            "type": r[3],
            "type_label": labels.get(r[3], r[3]),
            "balance": float(r[4] or 0),
            "abs_balance": abs(float(r[4] or 0)),
            "lines": int(r[5] or 0),
        } for r in rows]

    @api.model
    def _cash_flow(self, companies, date_from, date_to):
        """Kassa/bank hisoblari bo'yicha davr harakati."""
        self.env.cr.execute("""
            SELECT a.id, a.name->>'en_US',
                   SUM(l.debit) AS kirim, SUM(l.credit) AS chiqim,
                   SUM(l.balance) AS oqim
              FROM account_move_line l
              JOIN account_account a ON a.id = l.account_id
             WHERE l.parent_state = 'posted'
               AND l.company_id = ANY(%s)
               AND l.date >= %s AND l.date <= %s
               AND a.account_type IN ('asset_cash', 'liability_credit_card')
             GROUP BY 1, 2
             ORDER BY SUM(l.debit) DESC
        """, (companies, date_from, date_to))
        rows = self.env.cr.fetchall()
        accounts = self.env["account.account"].sudo().browse([r[0] for r in rows])
        name = {a.id: a.display_name for a in accounts}

        # davr boshidagi qoldiq
        self.env.cr.execute("""
            SELECT l.account_id, SUM(l.balance)
              FROM account_move_line l
              JOIN account_account a ON a.id = l.account_id
             WHERE l.parent_state = 'posted'
               AND l.company_id = ANY(%s) AND l.date < %s
               AND a.account_type IN ('asset_cash', 'liability_credit_card')
             GROUP BY 1
        """, (companies, date_from))
        opening = {r[0]: float(r[1] or 0) for r in self.env.cr.fetchall()}

        out = []
        for r in rows:
            op = opening.get(r[0], 0.0)
            flow = float(r[4] or 0)
            out.append({
                "id": r[0],
                "name": name.get(r[0]) or (r[1] or ""),
                "opening": op,
                "in": float(r[2] or 0),
                "out": float(r[3] or 0),
                "flow": flow,
                "closing": op + flow,
            })
        return out

    @api.model
    def _unposted_count(self, companies):
        """Tasdiqlanmagan (draft) provodkalar — hisobot to'liqligi uchun."""
        self.env.cr.execute("""
            SELECT COUNT(*) FROM account_move
             WHERE state = 'draft' AND company_id = ANY(%s)
        """, (companies,))
        return int((self.env.cr.fetchone() or [0])[0] or 0)

    @api.model
    def open_finance(self, kind, key=None, period=None, date_from=None,
                     date_to=None):
        """Moliya bo'limidan Odoo'ning provodkalar ro'yxatiga o'tish."""
        self._check_finance()
        d_from, d_to = self._period_dates(period or "month", date_from, date_to)

        types = []
        name = _("Provodkalar")
        domain = [("parent_state", "=", "posted"),
                  ("company_id", "in", self.env.companies.ids)]

        if kind == "balance":
            for k, label, tps, side in self.BS_GROUPS:
                if k == key:
                    types, name = list(tps), label
                    break
            domain += [("date", "<=", fields.Date.to_string(d_to))]
        elif kind == "pnl":
            for k, label, tps, sign in self.PL_GROUPS:
                if k == key:
                    types, name = list(tps), label
                    break
            domain += [("date", ">=", fields.Date.to_string(d_from)),
                       ("date", "<=", fields.Date.to_string(d_to))]
        elif kind == "account":
            domain += [("account_id", "=", int(key)),
                       ("date", "<=", fields.Date.to_string(d_to))]
            acc = self.env["account.account"].sudo().browse(int(key))
            name = acc.display_name
        elif kind == "cash":
            domain += [("account_id", "=", int(key)),
                       ("date", ">=", fields.Date.to_string(d_from)),
                       ("date", "<=", fields.Date.to_string(d_to))]
            acc = self.env["account.account"].sudo().browse(int(key))
            name = acc.display_name
        else:
            raise AccessError(_("Noma'lum bo'lim: %s", kind))

        if types:
            domain += [("account_id.account_type", "in", types)]

        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.move.line",
            "domain": domain,
            "views": [(False, "list"), (False, "form")],
            "target": "current",
            "context": {"search_default_group_by_account": 1},
        }

    # ================================================================== #
    #  13 · DO'KON KARTASI (panel ichida to'liq kesim)                    #
    # ================================================================== #
    @api.model
    def get_store_detail(self, store, period="today", date_from=None,
                         date_to=None):
        self._check_sales_access()
        configs = self._scoped_configs(store)
        if not configs:
            raise AccessError(_("Bu do'konni ko'rish huquqi yo'q."))

        d_from, d_to = self._period_dates(period, date_from, date_to)
        totals = self._totals(configs, d_from, d_to)
        kpi = self._kpis(totals)

        p_from, p_to = self._prev_period(d_from, d_to)
        prev = self._kpis(self._totals(configs, p_from, p_to))
        lfl_from, lfl_to = self._lfl_period(d_from, d_to)
        lfl = self._kpis(self._totals(configs, lfl_from, lfl_to))

        target = self.env["feliza.sales.target"].get_period_target(
            configs.ids, d_from, d_to)

        data = {
            "store": store,
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "registers": [c.name for c in configs],
            "kpi": kpi,
            "delta": {k: self._pct_delta(kpi.get(k), prev.get(k))
                      for k in ("revenue", "orders", "avg_check", "upt")},
            "lfl": self._pct_delta(kpi["revenue"], lfl["revenue"]),
            "target": target,
            "target_pct": (kpi["revenue"] / target * 100.0) if target else None,
            "units": totals.get("units", 0.0),
            "returns": totals.get("returns", 0.0),
            "return_orders": totals.get("return_orders", 0),
            "discount": totals.get("discount", 0.0),
            "payments": self._payments(configs, d_from, d_to),
            "hourly": [h for h in self._hourly(configs, d_from, d_to)
                       if h["revenue"]],
            "top_products": self._top_products(configs, d_from, d_to, limit=10),
            "sellers": self._salespeople(configs, d_from, d_to)[:10],
            "cashiers": self._cashiers(configs, d_from, d_to)[:10],
        }
        if self._show_cost():
            data["cost"] = totals.get("cost", 0.0)
            data["margin"] = totals.get("margin", 0.0)
            data["profit"] = totals.get("profit", 0.0)
        return data

    # ================================================================== #
    #  14 · KASSA SESSIYALARI — kim qachon ochdi, kim yopdi               #
    # ================================================================== #
    #  Ochgan   : pos.session.user_id (Odoo sessiyani ochgan xodimni
    #             shu maydonga yozadi)
    #  Yopgan   : yopilish provodkasini yaratgan foydalanuvchi
    #             (session.move_id.create_uid) — bu eng ishonchli manba.
    #             Provodka bo'lmasa — oxirgi o'zgartirgan (write_uid).
    # ------------------------------------------------------------------ #
    @api.model
    def _session_rows(self, configs, date_from, date_to, limit=80):
        if not configs:
            return []
        dt_from, dt_to = self._bounds(date_from, date_to)
        Session = self.env["pos.session"].sudo()

        sessions = Session.search([
            ("config_id", "in", configs.ids),
            "|",
            "&", ("start_at", ">=", dt_from), ("start_at", "<=", dt_to),
            ("state", "!=", "closed"),
        ], order="start_at desc", limit=limit)
        if not sessions:
            return []

        # sotuv jamlanmasi
        self.env.cr.execute("""
            SELECT o.session_id, COUNT(*), COALESCE(SUM(o.amount_total), 0)
              FROM pos_order o
             WHERE o.session_id = ANY(%s) AND o.state = ANY(%s)
             GROUP BY 1
        """, (sessions.ids, list(POS_DONE_STATES)))
        sales = {r[0]: (int(r[1] or 0), float(r[2] or 0))
                 for r in self.env.cr.fetchall()}

        # Sessiya davomidagi NAQD tushum — "kassa sanalmagan" holatini
        # aniqlash uchun kerak (pastdagi izohga qarang).
        self.env.cr.execute("""
            SELECT o.session_id, COALESCE(SUM(p.amount), 0)
              FROM pos_payment p
              JOIN pos_order o ON o.id = p.pos_order_id
              JOIN pos_payment_method m ON m.id = p.payment_method_id
             WHERE o.session_id = ANY(%s) AND o.state = ANY(%s)
               AND m.is_cash_count IS TRUE
             GROUP BY 1
        """, (sessions.ids, list(POS_DONE_STATES)))
        cash_sales = {r[0]: float(r[1] or 0) for r in self.env.cr.fetchall()}

        tz = self._tz()

        def loc(dt):
            if not dt:
                return ""
            return pytz.UTC.localize(dt).astimezone(tz).strftime("%d.%m %H:%M")

        rows = []
        for s in sessions:
            closer = s.move_id.create_uid if s.move_id else s.write_uid
            cnt, rev = sales.get(s.id, (0, 0.0))
            cash_in = cash_sales.get(s.id, 0.0)
            # "KASSA SANALMAGAN": sessiya yopilgan, naqd sotuv bo'lgan,
            # lekin kassir yopishda sanalgan naqdni KIRITMAGAN (0 qoldirgan).
            # Odoo bu holatda butun kunlik naqdni "kamomad" deb yozadi —
            # aslida pul yo'qolgani emas, shunchaki sanalmagani. Bu ikkisini
            # ajratmasak, hisobot rahbarni chalg'itadi.
            not_counted = bool(
                s.state == "closed"
                and cash_in > 0.01
                and abs(s.cash_register_balance_end_real or 0.0) < 0.01
            )
            hours = None
            if s.start_at:
                end = s.stop_at or datetime.utcnow()
                hours = (end - s.start_at).total_seconds() / 3600.0
            rows.append({
                "id": s.id,
                "name": s.name,
                "store": (s.config_id.feliza_store_group or "").strip()
                         or s.config_id.name,
                "register": s.config_id.name,
                "state": s.state,
                "state_label": dict(
                    s._fields["state"]._description_selection(self.env)
                ).get(s.state, s.state),
                "opened_at": loc(s.start_at),
                "opened_by": s.user_id.display_name or "",
                "closed_at": loc(s.stop_at),
                "closed_by": (closer.display_name or "") if closer and s.state == "closed" else "",
                "hours": hours or 0.0,
                "orders": cnt,
                "revenue": rev,
                "cash_start": s.cash_register_balance_start or 0.0,
                "cash_end": (s.cash_register_balance_end_real or 0.0)
                            if s.state == "closed" else 0.0,
                # ochiq sessiyada "farq" ma'noga ega emas — kassa hali
                # sanalmagan, shuning uchun 0 ko'rsatiladi
                "cash_sales": cash_in,
                "difference": (s.cash_register_difference or 0.0)
                              if s.state == "closed" else 0.0,
                "not_counted": not_counted,
                "opening_notes": s.opening_notes or "",
                "closing_notes": s.closing_notes or "",
            })
        return rows

    @api.model
    def get_sessions(self, period="today", date_from=None, date_to=None,
                     store=None, limit=150):
        self._check_sales_access()
        configs = self._scoped_configs(store)
        d_from, d_to = self._period_dates(period, date_from, date_to)
        # jamlanma BARCHA sessiyalar bo'yicha, ro'yxat esa limit bilan
        all_rows = self._session_rows(configs, d_from, d_to, limit=1000)
        rows = all_rows[:limit]

        opened = [r for r in all_rows if r["state"] != "closed"]
        return {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "rows": rows,
            "total": len(all_rows),
            "shown": len(rows),
            "truncated": len(all_rows) > len(rows),
            "open_count": len(opened),
            "closed_count": len(all_rows) - len(opened),
            "diff_total": sum(r["difference"] for r in all_rows),
            "diff_count": sum(1 for r in all_rows if abs(r["difference"]) > 0.01),
            # Kamomadning qancha qismi HAQIQIY, qanchasi shunchaki
            # "kassa sanalmagan" — bu ikkisi butunlay boshqa muammo.
            "not_counted_count": sum(1 for r in all_rows if r.get("not_counted")),
            "not_counted_total": sum(r["difference"] for r in all_rows
                                     if r.get("not_counted")),
            "real_diff_total": sum(r["difference"] for r in all_rows
                                   if not r.get("not_counted")),
            "revenue": sum(r["revenue"] for r in all_rows),
            "orders": sum(r["orders"] for r in all_rows),
        }

    @api.model
    def get_session_detail(self, session_id):
        self._check_access_dashboard()
        configs = self._allowed_configs()
        s = self.env["pos.session"].sudo().browse(int(session_id))
        if not s.exists() or s.config_id.id not in configs.ids:
            raise AccessError(_("Bu sessiyani ko'rish huquqi yo'q."))

        tz = self._tz()

        def loc(dt):
            if not dt:
                return ""
            return pytz.UTC.localize(dt).astimezone(tz).strftime("%d.%m.%Y %H:%M")

        closer = s.move_id.create_uid if s.move_id else s.write_uid
        orders = self.env["pos.order"].sudo().search([
            ("session_id", "=", s.id),
            ("state", "in", list(POS_DONE_STATES)),
        ], order="date_order desc")

        # to'lov turlari
        self.env.cr.execute("""
            SELECT m.id, m.name->>'en_US', SUM(p.amount), COUNT(*)
              FROM pos_payment p
              JOIN pos_order o ON o.id = p.pos_order_id
              JOIN pos_payment_method m ON m.id = p.payment_method_id
             WHERE o.session_id = %s AND o.state = ANY(%s)
             GROUP BY 1, 2 ORDER BY 3 DESC
        """, (s.id, list(POS_DONE_STATES)))
        pay_rows = self.env.cr.fetchall()
        methods = self.env["pos.payment.method"].sudo().browse(
            [r[0] for r in pay_rows])
        m_by_id = {m.id: m for m in methods}
        payments = [{
            "name": (m_by_id[r[0]].name if r[0] in m_by_id else (r[1] or "?")),
            "amount": float(r[2] or 0),
            "count": int(r[3] or 0),
            "is_cash": bool(getattr(m_by_id.get(r[0]), "is_cash_count", False)),
        } for r in pay_rows]

        show_cost = self._show_cost()
        revenue = sum(orders.mapped("amount_total"))
        units = sum(orders.mapped("lines").mapped("qty"))

        data = {
            "id": s.id,
            "name": s.name,
            "store": (s.config_id.feliza_store_group or "").strip() or s.config_id.name,
            "register": s.config_id.name,
            "state": s.state,
            "opened_at": loc(s.start_at),
            "opened_by": s.user_id.display_name or "",
            "closed_at": loc(s.stop_at),
            "closed_by": (closer.display_name or "") if closer and s.state == "closed" else "",
            "hours": ((s.stop_at or datetime.utcnow()) - s.start_at).total_seconds() / 3600.0
                     if s.start_at else 0.0,
            "orders": len(orders),
            "revenue": revenue,
            "units": units,
            "avg_check": revenue / len(orders) if orders else 0.0,
            "cash_start": s.cash_register_balance_start or 0.0,
            "cash_expected": s.cash_register_balance_end or 0.0,
            "cash_end": (s.cash_register_balance_end_real or 0.0)
                        if s.state == "closed" else 0.0,
            "difference": (s.cash_register_difference or 0.0)
                          if s.state == "closed" else 0.0,
            "is_open": s.state != "closed",
            "opening_notes": s.opening_notes or "",
            "closing_notes": s.closing_notes or "",
            "payments": payments,
            "order_list": [{
                "id": o.id,
                "ref": o.pos_reference or o.name,
                "time": pytz.UTC.localize(o.date_order).astimezone(tz).strftime("%H:%M")
                        if o.date_order else "",
                "cashier": o.user_id.display_name or "",
                "total": o.amount_total,
                "qty": sum(o.lines.mapped("qty")),
            } for o in orders[:25]],
        }
        if show_cost:
            cost = 0.0
            for o in orders:
                for l in o.lines:
                    cost += (l.product_id.standard_price or 0.0) * (l.qty or 0.0)
            data["cost"] = cost
            data["profit"] = revenue - cost
            data["margin"] = (revenue - cost) / revenue * 100.0 if revenue else 0.0
        return data

    # ================================================================== #
    #  10 · ZAKUPCHI PANELI                                               #
    # ================================================================== #
    #  Zakupchi uchun alohida bo'lim: yo'ldagi yuklar (tasdiqlangan, lekin
    #  hali kelmagan zakuplar), davrdagi xaridlar, ta'minotchilar va
    #  tugab borayotgan tovarlar.
    #
    #  XAVFSIZLIK: bo'lim faqat "Dashboard: Zakupchi" va "Rahbar"
    #  guruhlariga ochiq. Zakup summalari — zakupchining O'Z ish sohasi,
    #  shuning uchun ko'rinadi. SOTUV summalari va marja bu bo'limda
    #  UMUMAN yuborilmaydi — faqat sotilgan DONA (tovarni qayta buyurtma
    #  qilish uchun kerak bo'lgani uchun).
    # ------------------------------------------------------------------ #
    @api.model
    def _is_purchase_user(self):
        return self.env.user.has_group(GROUP_PURCHASE)

    @api.model
    def _check_zakup_access(self):
        if not (self._is_manager() or self._is_purchase_user()):
            raise AccessError(_("Zakup bo'limi sizga ochiq emas."))

    @api.model
    def _zakup_pul(self, valyuta_summa):
        """{valyuta: summa} -> ko'rsatishga tayyor ro'yxat (katta oldinda)."""
        return [{"cur": k, "amount": v}
                for k, v in sorted(valyuta_summa.items(),
                                   key=lambda kv: -abs(kv[1]))]

    @api.model
    def get_zakup(self, period="month", date_from=None, date_to=None,
                  store=None):
        self._check_zakup_access()
        d_from, d_to = self._period_dates(period, date_from, date_to)
        dt_from, dt_to = self._bounds(d_from, d_to)
        transit = self._zakup_transit()
        return {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "kpi": self._zakup_kpi(dt_from, dt_to, transit),
            "transit": transit,
            "transit_products": self._zakup_transit_products(),
            "suppliers": self._zakup_suppliers(dt_from, dt_to),
            "recent": self._zakup_recent(),
            "low_stock": self._zakup_low_stock(),
        }

    def _zakup_pending_sql(self):
        """Yo'ldagi (kutilayotgan) zakup kirimlari — FROM/JOIN/WHERE qismi."""
        return """
            FROM stock_picking sp
            JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            JOIN LATERAL (
                SELECT l.order_id
                  FROM stock_move mm
                  JOIN purchase_order_line l ON l.id = mm.purchase_line_id
                 WHERE mm.picking_id = sp.id
                 LIMIT 1) zpo ON TRUE
            JOIN purchase_order po ON po.id = zpo.order_id
            LEFT JOIN res_partner rp ON rp.id = po.partner_id
            LEFT JOIN res_currency rc ON rc.id = po.currency_id
           WHERE spt.code = 'incoming'
             AND sp.state NOT IN ('done', 'cancel')
        """

    @api.model
    def _zakup_kpi(self, dt_from, dt_to, transit_rows):
        cr = self.env.cr

        # --- hozir yo'lda (transit ro'yxatidan jamlanadi) ---
        yolda_docs = len(transit_rows)
        yolda_qty = sum(r["qty"] for r in transit_rows)
        yolda_late = sum(1 for r in transit_rows if r["late_days"] > 0)
        yolda_pul = {}
        for r in transit_rows:
            if r["cur"]:
                yolda_pul[r["cur"]] = yolda_pul.get(r["cur"], 0.0) + r["amount"]

        # --- qoralama so'rovlar ---
        cr.execute("""SELECT COUNT(*) FROM purchase_order
                       WHERE state IN ('draft', 'sent')""")
        qoralama = cr.fetchone()[0]

        # --- davrda buyurtma qilingan ---
        cr.execute("""
            SELECT COUNT(DISTINCT po.id),
                   COALESCE(SUM(l.product_qty), 0)
              FROM purchase_order po
              LEFT JOIN purchase_order_line l ON l.order_id = po.id
             WHERE po.state IN ('purchase', 'done')
               AND po.date_order >= %s AND po.date_order <= %s
        """, (dt_from, dt_to))
        buyurtma_docs, buyurtma_qty = cr.fetchone()

        cr.execute("""
            SELECT rc.name, COALESCE(SUM(po.amount_total), 0)
              FROM purchase_order po
              JOIN res_currency rc ON rc.id = po.currency_id
             WHERE po.state IN ('purchase', 'done')
               AND po.date_order >= %s AND po.date_order <= %s
             GROUP BY rc.name
        """, (dt_from, dt_to))
        buyurtma_pul = dict(cr.fetchall())

        # --- davrda qabul qilingan ---
        cr.execute("""
            SELECT COUNT(DISTINCT sp.id), COALESCE(SUM(m.quantity), 0)
              FROM stock_picking sp
              JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
              JOIN stock_move m ON m.picking_id = sp.id AND m.state = 'done'
             WHERE spt.code = 'incoming'
               AND m.purchase_line_id IS NOT NULL
               AND sp.state = 'done'
               AND sp.date_done >= %s AND sp.date_done <= %s
        """, (dt_from, dt_to))
        kelgan_docs, kelgan_qty = cr.fetchone()

        return {
            "transit_docs": yolda_docs,
            "transit_qty": int(yolda_qty),
            "transit_late": yolda_late,
            "transit_money": self._zakup_pul(yolda_pul),
            "draft_count": int(qoralama or 0),
            "ordered_docs": int(buyurtma_docs or 0),
            "ordered_qty": int(buyurtma_qty or 0),
            "ordered_money": self._zakup_pul(buyurtma_pul),
            "arrived_docs": int(kelgan_docs or 0),
            "arrived_qty": int(kelgan_qty or 0),
        }

    @api.model
    def _zakup_transit(self, limit=200):
        """Yo'ldagi yuklar — har bir kutilayotgan kirim hujjati."""
        cr = self.env.cr
        cr.execute("""
            SELECT sp.id, sp.name, po.id, po.name, rp.name,
                   po.date_order::date, sp.scheduled_date::date,
                   po.amount_total, rc.name,
                   (SELECT COALESCE(SUM(product_uom_qty), 0) FROM stock_move
                     WHERE picking_id = sp.id
                       AND state NOT IN ('done','cancel')),
                   (SELECT COUNT(*) FROM stock_move
                     WHERE picking_id = sp.id
                       AND state NOT IN ('done','cancel'))
        """ + self._zakup_pending_sql() + """
             ORDER BY sp.scheduled_date
             LIMIT %s
        """, (limit,))
        today = self._today()
        rows = []
        for (pid, nom, po_id, po_nom, tk, sana, reja, summa, val,
             qty, lines) in cr.fetchall():
            kech = (today - reja).days if reja else 0
            rows.append({
                "id": pid, "name": nom,
                "po_id": po_id, "po_name": po_nom or "-",
                "supplier": tk or "-",
                "date": sana.strftime("%d.%m") if sana else "-",
                "expected": reja.strftime("%d.%m") if reja else "-",
                "amount": float(summa or 0), "cur": val or "",
                "qty": int(qty or 0), "lines": int(lines or 0),
                "late_days": max(kech, 0),
            })
        return rows

    @api.model
    def _zakup_transit_products(self, limit=20):
        """Yo'lda kutilayotgan tovarlar (dona bo'yicha eng kattalari)."""
        cr = self.env.cr
        cr.execute("""
            SELECT pt.name->>'en_US',
                   COALESCE(pp.default_code, pt.default_code, ''),
                   SUM(m.product_uom_qty)::int,
                   COUNT(DISTINCT sp.id)
              FROM stock_move m
              JOIN stock_picking sp ON sp.id = m.picking_id
              JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
              JOIN product_product pp ON pp.id = m.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE spt.code = 'incoming'
               AND sp.state NOT IN ('done', 'cancel')
               AND m.purchase_line_id IS NOT NULL
               AND m.state NOT IN ('done', 'cancel')
             GROUP BY 1, 2
             ORDER BY 3 DESC
             LIMIT %s
        """, (limit,))
        return [{"name": n or "-", "code": k or "", "qty": q, "docs": d}
                for n, k, q, d in cr.fetchall()]

    @api.model
    def _zakup_suppliers(self, dt_from, dt_to, limit=20):
        """Davrdagi ta'minotchilar — buyurtma, dona va summa."""
        cr = self.env.cr
        cr.execute("""
            SELECT rp.name, rc.name,
                   COUNT(DISTINCT po.id),
                   COALESCE(SUM(l.product_qty), 0)::int,
                   COALESCE(SUM(l.price_unit * l.product_qty), 0)
              FROM purchase_order po
              JOIN res_partner rp ON rp.id = po.partner_id
              JOIN res_currency rc ON rc.id = po.currency_id
              LEFT JOIN purchase_order_line l ON l.order_id = po.id
             WHERE po.state IN ('purchase', 'done')
               AND po.date_order >= %s AND po.date_order <= %s
             GROUP BY 1, 2
             ORDER BY 5 DESC
             LIMIT %s
        """, (dt_from, dt_to, limit))
        return [{"supplier": s or "-", "cur": c or "",
                 "orders": int(o), "qty": q, "amount": float(a)}
                for s, c, o, q, a in cr.fetchall()]

    @api.model
    def _zakup_recent(self, limit=12):
        """So'nggi qabul qilingan yuklar."""
        cr = self.env.cr
        cr.execute("""
            SELECT sp.id, sp.name, rp.name, po.name,
                   sp.date_done,
                   (SELECT COALESCE(SUM(quantity), 0) FROM stock_move
                     WHERE picking_id = sp.id AND state = 'done')::int
              FROM stock_picking sp
              JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
              JOIN LATERAL (
                  SELECT l.order_id FROM stock_move mm
                    JOIN purchase_order_line l ON l.id = mm.purchase_line_id
                   WHERE mm.picking_id = sp.id LIMIT 1) zpo ON TRUE
              JOIN purchase_order po ON po.id = zpo.order_id
              LEFT JOIN res_partner rp ON rp.id = sp.partner_id
             WHERE spt.code = 'incoming'
               AND sp.state = 'done'
             ORDER BY sp.date_done DESC
             LIMIT %s
        """, (limit,))
        tz = self._tz()
        rows = []
        for pid, nom, tk, po_nom, dd, qty in cr.fetchall():
            if dd:
                dd = pytz.UTC.localize(dd).astimezone(tz)
            rows.append({
                "id": pid, "name": nom, "supplier": tk or "-",
                "po_name": po_nom or "-",
                "date": dd.strftime("%d.%m %H:%M") if dd else "-",
                "qty": qty or 0,
            })
        return rows

    @api.model
    def _zakup_low_stock(self, days=14, limit=20):
        """Tugab borayotgan tovarlar — qayta buyurtma nomzodlari.

        So'nggi {days} kunda sotilgan, lekin qoldig'i sotuv sur'atidan
        kam qolgan tovarlar. Bu bo'limda SUMMALAR YO'Q — faqat dona:
        zakupchiga nechta kerakligi shu bilan ayon.
        """
        cr = self.env.cr
        cr.execute("""
            WITH sotuv AS (
                SELECT l.product_id, SUM(l.qty)::int AS sotilgan
                  FROM pos_order_line l
                  JOIN pos_order o ON o.id = l.order_id
                 WHERE o.state IN ('paid', 'done', 'invoiced')
                   AND o.date_order >= NOW() - INTERVAL '%s day'
                 GROUP BY l.product_id
                HAVING SUM(l.qty) >= 5
            ), qoldiq AS (
                SELECT q.product_id, SUM(q.quantity)::int AS bor
                  FROM stock_quant q
                  JOIN stock_location sl ON sl.id = q.location_id
                 WHERE sl.usage = 'internal'
                 GROUP BY q.product_id
            )
            SELECT pt.name->>'en_US',
                   COALESCE(pp.default_code, pt.default_code, ''),
                   s.sotilgan, COALESCE(k.bor, 0),
                   (SELECT COALESCE(SUM(m.product_uom_qty), 0) FROM stock_move m
                     WHERE m.product_id = s.product_id
                       AND m.purchase_line_id IS NOT NULL
                       AND m.state NOT IN ('done','cancel'))::int
              FROM sotuv s
              LEFT JOIN qoldiq k ON k.product_id = s.product_id
              JOIN product_product pp ON pp.id = s.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE COALESCE(k.bor, 0) <= s.sotilgan
             ORDER BY (COALESCE(k.bor, 0)::float / s.sotilgan)
             LIMIT %s
        """ % (int(days), int(limit)))
        rows = []
        for nom, kod, sotilgan, bor, yolda in cr.fetchall():
            kunga = round(bor / (sotilgan / float(days)), 1) if sotilgan else 0
            rows.append({
                "name": nom or "-", "code": kod or "",
                "sold": sotilgan, "stock": bor, "incoming": yolda,
                "cover_days": kunga,
            })
        return rows

    # ================================================================== #
    #  11 · ZAKUPCHI STATISTIKASI (Sotuvlarim / Skladim / Daromadim)      #
    # ================================================================== #
    #  Har bir zakupchi FAQAT o'zi yaratgan yoki o'zi zakup qilgan
    #  tovarlarni ko'radi. Qamrov SERVERDA aniqlanadi: oddiy zakupchi
    #  boshqa foydalanuvchi id sini yuborsa ham, baribir o'zining
    #  tovarlari qaytadi. Faqat rahbar boshqa zakupchini tanlay oladi.
    #
    #  DAROMAD (komissiya) HECH QAYERDA SAQLANMAYDI — har safar sotuvdan
    #  jonli hisoblanadi: O'zbekiston tovari uchun sotuv summasining
    #  1.5%, boshqa davlat tovari uchun 1%.
    # ------------------------------------------------------------------ #
    ZAKUPCHI_UZB = ("o'zbekiston", "ozbekiston", "uzb", "uzbekistan",
                    "узбекистан", "uz")
    _POS_DONE_SQL = "('paid', 'done', 'invoiced')"

    # Eski/migratsiya tovarlari zakupchisi `x_zakup_qilgan` (matn) da yozilgan,
    # `create_uid` esa admin/import. Shu bilan bog'lash uchun: uid -> (include,
    # exclude) LIKE naqshlari. Ikki kishilik ("Razida Qunduz") FAQAT Razidaga
    # (Qunduzda 'razida' bor bo'lsa chiqarib tashlanadi).
    ZAKUP_NAME_MATCH = {
        7:  ("%razida%", None),         # Razida Masharipova (razida.m)
        54: ("%qunduz%", "%razida%"),   # Xasanova Qunduzxon (xasanova.171)
    }

    @api.model
    def _zakupchi_uid(self, zakupchi=None):
        """Qaysi zakupchining ma'lumoti: oddiy zakupchi — faqat o'ziniki."""
        self._check_zakup_access()
        if self._is_manager() and zakupchi:
            return int(zakupchi) if zakupchi != "all" else None
        return self.env.uid

    @api.model
    def _zakupchi_scope_cte(self, uid):
        """(CTE matni, parametrlar) — zakupchining tovarlari."""
        if uid is None:                    # rahbar: barcha tovarlar
            return ("scope AS (SELECT id AS product_id FROM product_product)",
                    {})
        params = {"zuid": uid}
        body = """
            SELECT pp.id AS product_id
              FROM product_product pp
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE pt.create_uid = %(zuid)s
            UNION
            SELECT pol.product_id
              FROM purchase_order_line pol
              JOIN purchase_order po ON po.id = pol.order_id
             WHERE po.state IN ('purchase', 'done')
               AND (po.user_id = %(zuid)s OR po.create_uid = %(zuid)s)"""
        # Eski tovarlar: `x_zakup_qilgan` (matn) bo'yicha ham bog'lash
        match = self.ZAKUP_NAME_MATCH.get(uid)
        if match:
            inc, exc = match
            params["zinc"] = inc
            cond = "LOWER(COALESCE(pt.x_zakup_qilgan, '')) LIKE %(zinc)s"
            if exc:
                params["zexc"] = exc
                cond += (" AND LOWER(COALESCE(pt.x_zakup_qilgan, '')) "
                         "NOT LIKE %(zexc)s")
            body += """
            UNION
            SELECT pp.id AS product_id
              FROM product_product pp
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE """ + cond
        return ("scope AS (" + body + "\n        )", params)

    @api.model
    def _zakupchi_attr_ids(self):
        cr = self.env.cr
        cr.execute("""SELECT id, LOWER(COALESCE(name->>'en_US', ''))
                        FROM product_attribute""")
        rang = olcham = -1
        for aid, nom in cr.fetchall():
            if nom == "rang":
                rang = aid
            elif nom in ("o'lcham", "olcham", "o‘lcham"):
                olcham = aid
        return rang, olcham

    @api.model
    def _zakupchi_attr_lateral(self):
        return """
            LEFT JOIN LATERAL (
                SELECT pav.name->>'en_US' AS v
                  FROM product_variant_combination pvc
                  JOIN product_template_attribute_value ptav
                       ON ptav.id = pvc.product_template_attribute_value_id
                  JOIN product_attribute_value pav
                       ON pav.id = ptav.product_attribute_value_id
                 WHERE pvc.product_product_id = pp.id
                   AND pav.attribute_id = %(rang_id)s LIMIT 1) rangv ON TRUE
            LEFT JOIN LATERAL (
                SELECT pav.name->>'en_US' AS v
                  FROM product_variant_combination pvc
                  JOIN product_template_attribute_value ptav
                       ON ptav.id = pvc.product_template_attribute_value_id
                  JOIN product_attribute_value pav
                       ON pav.id = ptav.product_attribute_value_id
                 WHERE pvc.product_product_id = pp.id
                   AND pav.attribute_id = %(olcham_id)s LIMIT 1) olch ON TRUE
        """

    @api.model
    def _zakupchi_country_col(self):
        """Davlat ustuni bor-yo'qligi (Studio maydoni)."""
        cr = self.env.cr
        cr.execute("""SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'product_template'
                         AND column_name = 'x_studio_ishlab_chiqarilgan_davlat'""")
        return bool(cr.fetchone())

    # ------------------------------------------------------------------ #
    #  11.1  SOTUVLARIM                                                   #
    # ------------------------------------------------------------------ #
    @api.model
    def get_zakupchi_sales(self, period="month", date_from=None, date_to=None,
                           status="top", query="", categ="", color="",
                           size="", zakupchi=None, limit=400):
        uid = self._zakupchi_uid(zakupchi)
        d_from, d_to = self._period_dates(period, date_from, date_to)
        dt_from, dt_to = self._bounds(d_from, d_to)
        davr_kun = max((d_to - d_from).days + 1, 1)
        cte, params = self._zakupchi_scope_cte(uid)
        rang_id, olcham_id = self._zakupchi_attr_ids()
        comp = str(self.env.company.id)
        params.update({"dfrom": dt_from, "dto": dt_to, "comp": comp,
                       "rang_id": rang_id, "olcham_id": olcham_id,
                       "limit": int(limit)})

        shart = ["pp.active"]
        if query:
            params["q"] = "%" + query.strip() + "%"
            shart.append("""(pt.name->>'en_US' ILIKE %(q)s
                            OR pp.default_code ILIKE %(q)s
                            OR pt.default_code ILIKE %(q)s
                            OR pp.barcode ILIKE %(q)s)""")
        if categ:
            params["categ"] = categ
            shart.append("pc.complete_name = %(categ)s")
        if color:
            params["color"] = color
            shart.append("rangv.v = %(color)s")
        if size:
            params["size"] = size
            shart.append("olch.v = %(size)s")

        if status == "top":
            shart.append("COALESCE(s.dona, 0) > 0")
            tartib = "COALESCE(s.dona, 0) DESC"
        elif status == "profit":
            shart.append("COALESCE(s.dona, 0) > 0")
            tartib = """(COALESCE(s.tushum, 0)
                        - COALESCE((pp.standard_price->>%(comp)s)::float, 0)
                          * COALESCE(s.dona, 0)) DESC"""
        elif status == "loss":
            shart.append("COALESCE(s.dona, 0) > 0")
            shart.append("""(COALESCE(s.tushum, 0)
                        - COALESCE((pp.standard_price->>%(comp)s)::float, 0)
                          * COALESCE(s.dona, 0)) <= 0.01""")
            tartib = """(COALESCE(s.tushum, 0)
                        - COALESCE((pp.standard_price->>%(comp)s)::float, 0)
                          * COALESCE(s.dona, 0)) ASC"""
        else:                                    # slow — savdosi past
            tartib = "COALESCE(s.dona, 0) ASC, pt.name->>'en_US'"

        cr = self.env.cr
        cr.execute("WITH " + cte + """,
            sot AS (
                SELECT l.product_id,
                       SUM(l.qty) AS dona,
                       SUM(l.price_subtotal_incl) AS tushum
                  FROM pos_order_line l
                  JOIN pos_order o ON o.id = l.order_id
                 WHERE o.state IN """ + self._POS_DONE_SQL + """
                   AND o.date_order >= %(dfrom)s AND o.date_order <= %(dto)s
                 GROUP BY l.product_id
            ),
            birinchi AS (
                SELECT l.product_id, MIN(o.date_order) AS boshi
                  FROM pos_order_line l
                  JOIN pos_order o ON o.id = l.order_id
                 WHERE o.state IN """ + self._POS_DONE_SQL + """
                 GROUP BY l.product_id
            )
            SELECT pp.id, pt.name->>'en_US',
                   COALESCE(pp.default_code, pt.default_code, ''),
                   pc.complete_name, rangv.v, olch.v,
                   COALESCE(s.dona, 0), COALESCE(s.tushum, 0),
                   COALESCE((pp.standard_price->>%(comp)s)::float, 0),
                   pt.list_price, b.boshi::date
              FROM product_product pp
              JOIN scope sc ON sc.product_id = pp.id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id AND pt.active
              JOIN product_category pc ON pc.id = pt.categ_id
              LEFT JOIN sot s ON s.product_id = pp.id
              LEFT JOIN birinchi b ON b.product_id = pp.id
        """ + self._zakupchi_attr_lateral() + """
             WHERE """ + " AND ".join(shart) + """
             ORDER BY """ + tartib + """
             LIMIT %(limit)s
        """, params)

        today = self._today()
        rows = []
        for (pid, nom, kod, kat, rang, olcham, dona, tushum,
             tan, ruyxat_narx, boshi) in cr.fetchall():
            dona = float(dona or 0)
            narx = (tushum / dona) if dona else float(ruyxat_narx or 0)
            marja_sum = tushum - tan * dona
            marja_pct = ((narx - tan) / tan * 100.0) if tan else 0.0
            rows.append({
                "id": pid, "name": nom or "-", "code": kod or "",
                "categ": (kat or "").split("/")[-1].strip(),
                "color": rang or "", "size": olcham or "",
                "days_selling": (today - boshi).days if boshi else 0,
                "per_day": round(dona / davr_kun, 2),
                "qty": int(dona),
                "cost": tan, "price": narx,
                "margin_pct": marja_pct, "margin_sum": marja_sum,
            })

        return {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "rows": rows,
            "filters": self._zakupchi_filters(uid),
        }

    @api.model
    def _zakupchi_filters(self, uid):
        """Filtr variantlari — qamrovdagi tovarlardan."""
        cte, params = self._zakupchi_scope_cte(uid)
        rang_id, olcham_id = self._zakupchi_attr_ids()
        params.update({"rang_id": rang_id, "olcham_id": olcham_id})
        cr = self.env.cr
        cr.execute("WITH " + cte + """
            SELECT DISTINCT pc.complete_name, rangv.v, olch.v
              FROM product_product pp
              JOIN scope sc ON sc.product_id = pp.id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id AND pt.active
              JOIN product_category pc ON pc.id = pt.categ_id
        """ + self._zakupchi_attr_lateral() + """
             WHERE pp.active
        """, params)
        cats, colors, sizes = set(), set(), set()
        for kat, rang, olcham in cr.fetchall():
            if kat:
                cats.add(kat)
            if rang:
                colors.add(rang)
            if olcham:
                sizes.add(olcham)
        return {"cats": sorted(cats), "colors": sorted(colors),
                "sizes": sorted(sizes)}

    # ------------------------------------------------------------------ #
    #  11.2  SKLADIM                                                      #
    # ------------------------------------------------------------------ #
    @api.model
    def get_zakupchi_stock(self, status="low", query="", zakupchi=None,
                           limit=400):
        uid = self._zakupchi_uid(zakupchi)
        cte, params = self._zakupchi_scope_cte(uid)
        rang_id, olcham_id = self._zakupchi_attr_ids()
        comp = str(self.env.company.id)
        params.update({"comp": comp, "rang_id": rang_id,
                       "olcham_id": olcham_id, "limit": int(limit)})

        shart = ["pp.active"]
        if query:
            params["q"] = "%" + query.strip() + "%"
            shart.append("""(pt.name->>'en_US' ILIKE %(q)s
                            OR pp.default_code ILIKE %(q)s
                            OR pt.default_code ILIKE %(q)s
                            OR pp.barcode ILIKE %(q)s)""")
        if status == "zero":
            shart.append("COALESCE(k.bor, 0) <= 0")
            tartib = "marja DESC"
        elif status == "high":
            shart.append("COALESCE(k.bor, 0) > 10")
            tartib = "COALESCE(k.bor, 0) DESC"
        else:                                    # low — kam qolgan
            shart.append("COALESCE(k.bor, 0) > 0 AND COALESCE(k.bor, 0) <= 10")
            tartib = "COALESCE(k.bor, 0) ASC"

        cr = self.env.cr
        cr.execute("WITH " + cte + """,
            qoldiq AS (
                SELECT q.product_id,
                       SUM(q.quantity) AS bor,
                       SUM(q.reserved_quantity) AS band
                  FROM stock_quant q
                  JOIN stock_location sl ON sl.id = q.location_id
                 WHERE sl.usage = 'internal'
                 GROUP BY q.product_id
            ),
            sot AS (
                SELECT l.product_id,
                       SUM(l.qty) AS dona,
                       SUM(l.price_subtotal_incl) AS tushum
                  FROM pos_order_line l
                  JOIN pos_order o ON o.id = l.order_id
                 WHERE o.state IN """ + self._POS_DONE_SQL + """
                 GROUP BY l.product_id
            )
            SELECT pp.id, pt.name->>'en_US',
                   COALESCE(pp.default_code, pt.default_code, ''),
                   rangv.v, olch.v,
                   COALESCE(k.bor, 0)::int, COALESCE(k.band, 0)::int,
                   (COALESCE(s.tushum, 0)
                    - COALESCE((pp.standard_price->>%(comp)s)::float, 0)
                      * COALESCE(s.dona, 0)) AS marja
              FROM product_product pp
              JOIN scope sc ON sc.product_id = pp.id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id AND pt.active
              LEFT JOIN qoldiq k ON k.product_id = pp.id
              LEFT JOIN sot s ON s.product_id = pp.id
        """ + self._zakupchi_attr_lateral() + """
             WHERE """ + " AND ".join(shart) + """
             ORDER BY """ + tartib + """
             LIMIT %(limit)s
        """, params)
        rows = [{
            "id": pid, "name": nom or "-", "code": kod or "",
            "color": rang or "", "size": olcham or "",
            "stock": bor, "reserved": band, "margin_sum": float(marja or 0),
        } for pid, nom, kod, rang, olcham, bor, band, marja in cr.fetchall()]
        return {"rows": rows}

    # ------------------------------------------------------------------ #
    #  11.3  DAROMADIM                                                    #
    # ------------------------------------------------------------------ #
    def _zakupchi_uzb_sql(self):
        """SQL: davlat O'zbekistonmi (1.5%) yoki emas (1%).

        DIQQAT: "o'zbekiston" ichida apostrof bor — ro'yxat SQL matniga
        emas, PARAMETR sifatida beriladi (%(uzb)s), aks holda sintaksis
        buziladi.
        """
        if self._zakupchi_country_col():
            davlat = "LOWER(TRIM(COALESCE(pt.x_studio_ishlab_chiqarilgan_davlat, '')))"
        else:
            davlat = "''"
        return davlat, "(%s IN %%(uzb)s)" % davlat

    @api.model
    def get_zakupchi_income(self, period="month", date_from=None,
                            date_to=None, query="", zakupchi=None):
        uid = self._zakupchi_uid(zakupchi)
        d_from, d_to = self._period_dates(period, date_from, date_to)
        dt_from, dt_to = self._bounds(d_from, d_to)
        cte, params = self._zakupchi_scope_cte(uid)
        tz = str(self._tz())
        davlat, uzb_sharti = self._zakupchi_uzb_sql()
        foiz = "CASE WHEN %s THEN 1.5 ELSE 1.0 END" % uzb_sharti
        params.update({"dfrom": dt_from, "dto": dt_to, "tz": tz,
                       "uzb": tuple(self.ZAKUPCHI_UZB)})

        asos = ("WITH " + cte + """
            SELECT (o.date_order AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date
                       AS kun,
                   c.name AS dokon,
                   COALESCE(NULLIF(TRIM(c.feliza_store_group), ''), c.name)
                       AS guruh,
                   """ + davlat + """ AS davlat,
                   """ + foiz + """ AS foiz,
                   l.qty, l.price_subtotal_incl AS summa,
                   l.price_subtotal_incl * (""" + foiz + """) / 100.0
                       AS daromad,
                   pp.id AS product_id,
                   pt.name->>'en_US' AS nom,
                   COALESCE(pp.default_code, pt.default_code, '') AS kod
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
              JOIN pos_config c ON c.id = o.config_id
              JOIN product_product pp ON pp.id = l.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
              JOIN scope sc ON sc.product_id = l.product_id
             WHERE o.state IN """ + self._POS_DONE_SQL + """
               AND o.date_order >= %(dfrom)s AND o.date_order <= %(dto)s
        """)
        cr = self.env.cr
        cr.execute("SELECT * FROM (" + asos + ") t", params)
        cols = [d[0] for d in cr.description]
        satrlar = [dict(zip(cols, r)) for r in cr.fetchall()]

        today = self._today()
        kunlik = {}
        davlat_b = {}
        dokon_b = {}
        jami = uzb = imp = bugun = 0.0
        for r in satrlar:
            d = float(r["daromad"] or 0)
            jami += d
            if float(r["foiz"]) == 1.5:
                uzb += d
            else:
                imp += d
            if r["kun"] == today:
                bugun += d
            kunlik[r["kun"]] = kunlik.get(r["kun"], 0.0) + d
            dn = (r["davlat"] or "").strip() or "ko'rsatilmagan"
            davlat_b.setdefault(dn, [0.0, float(r["foiz"])])
            davlat_b[dn][0] += d
            dokon_b[r["guruh"]] = dokon_b.get(r["guruh"], 0.0) + d

        # kunlik qator — davrning har bir kuni (bo'sh kunlar 0)
        daily = []
        k = d_from
        while k <= d_to:
            daily.append({"date": k.strftime("%d.%m"),
                          "amount": round(kunlik.get(k, 0.0))})
            k += timedelta(days=1)

        # tovar qidiruvi
        tovar = None
        if query:
            qq = query.strip().lower()
            mos = [r for r in satrlar
                   if qq in (r["nom"] or "").lower()
                   or qq in (r["kod"] or "").lower()]
            if mos:
                tovar = {
                    "name": mos[0]["nom"], "code": mos[0]["kod"],
                    "pct": float(mos[0]["foiz"]),
                    "country": (mos[0]["davlat"] or "").strip()
                               or "ko'rsatilmagan",
                    "qty": int(sum(float(r["qty"] or 0) for r in mos)),
                    "revenue": round(sum(float(r["summa"] or 0) for r in mos)),
                    "income": round(sum(float(r["daromad"] or 0) for r in mos)),
                }

        return {
            "period": {"from": str(d_from), "to": str(d_to), "key": period},
            "kpi": {"today": round(bugun), "total": round(jami),
                    "uzb": round(uzb), "imp": round(imp)},
            "daily": daily,
            "by_country": sorted(
                [{"country": (k[:1].upper() + k[1:]) if k != "ko'rsatilmagan"
                  else "Ko'rsatilmagan", "pct": v[1], "amount": round(v[0])}
                 for k, v in davlat_b.items()],
                key=lambda x: -x["amount"]),
            "by_store": sorted(
                [{"store": k, "amount": round(v)}
                 for k, v in dokon_b.items()], key=lambda x: -x["amount"]),
            "product": tovar,
            "product_not_found": bool(query) and tovar is None,
        }
