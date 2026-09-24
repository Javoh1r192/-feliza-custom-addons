# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FelizaInventorySession(models.Model):
    _name = 'feliza.inventory.session'
    _description = "Inventarizatsiya sessiyasi"
    _order = 'id desc'

    name = fields.Char("Raqam", default=lambda s: _('Yangi'), copy=False,
                       readonly=True, index=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', "Do'kon / Ombor", required=True,
        readonly=False, states={'done': [('readonly', True)],
                                'cancel': [('readonly', True)]})
    location_ids = fields.Many2many(
        'stock.location', string="Joylar", compute='_compute_location_ids',
        store=True,
        help="Shu ombordagi barcha ichki joylar (skanerlash mumkin bo'lganlar).")
    current_location_id = fields.Many2one(
        'stock.location', "Joriy joy", copy=False,
        help="Oxirgi skanerlangan lokatsiya. Tovarlar shu joyga sanaladi.")
    state = fields.Selection([
        ('draft', "Tayyorlanmoqda"),
        ('in_progress', "Sanalyapti"),
        ('done', "Yakunlangan"),
        ('cancel', "Bekor qilingan"),
    ], default='draft', required=True, copy=False, tracking=True, index=True)
    user_id = fields.Many2one('res.users', "Mas'ul",
                              default=lambda s: s.env.user)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    start_at = fields.Datetime("Boshlangan", readonly=True, copy=False)
    end_at = fields.Datetime("Tugagan", readonly=True, copy=False)
    applied = fields.Boolean("Astatkaga qo'llangan", readonly=True, copy=False)
    applied_at = fields.Datetime("Qo'llangan vaqt", readonly=True, copy=False)
    applied_by = fields.Many2one('res.users', "Qo'llagan", readonly=True,
                                 copy=False)
    duration_label = fields.Char("Davomiylik", compute='_compute_duration')
    note = fields.Char("Izoh")
    expected_start_json = fields.Text(readonly=True, copy=False)
    # Butun sklad bo'yicha KUTILGAN (sanash boshida muzlatiladi)
    expected_total_qty = fields.Float("Kutilgan jami (dona)", readonly=True,
                                      copy=False, digits='Product Unit of Measure')
    expected_total_types = fields.Integer("Kutilgan tovar turi", readonly=True,
                                          copy=False)
    expected_total_cost = fields.Monetary("Kutilgan jami (tannarx)",
                                          readonly=True, copy=False)
    expected_total_sale = fields.Monetary("Kutilgan jami (sotuv)",
                                          readonly=True, copy=False)
    line_ids = fields.One2many('feliza.inventory.line', 'session_id', "Qatorlar")
    product_ids = fields.One2many('feliza.inventory.product', 'session_id',
                                  "Mahsulot kesimi")
    scan_ids = fields.One2many('feliza.inventory.scan', 'session_id', "Skanlar")
    recent_scan_ids = fields.Many2many(
        'feliza.inventory.scan', string="So'nggi skanlar",
        compute='_compute_recent_scans',
        help="Jonli panel uchun faqat oxirgi 10 skan (tez, katta sessiyada ham).")
    cursor_ids = fields.One2many('feliza.inventory.cursor', 'session_id',
                                 "Kursorlar")
    scan_input = fields.Char("Skaner", store=False,
                             help="Lokatsiya yoki tovar barkodini skanerlang.")
    my_location_id = fields.Many2one('stock.location',
                                     "Mening joyim", compute='_compute_my_location',
                                     help="Sizning joriy joyingiz (har skaner alohida).")
    participants_label = fields.Char("Ishtirokchilar",
                                     compute='_compute_participants')
    scan_count = fields.Integer("Skanlar soni", compute='_compute_participants')

    # ---- yig'indilar ----
    product_count = fields.Integer("Tovar turi", compute='_compute_totals')
    expected_qty = fields.Float("Kutilgan (dona)", compute='_compute_totals')
    counted_qty = fields.Float("Sanalgan (dona)", compute='_compute_totals')
    sold_qty = fields.Float("Sotilgan (davomida)", compute='_compute_totals')
    surplus_qty = fields.Float("Ortiqcha (dona)", compute='_compute_totals')
    shortage_qty = fields.Float("Kam (dona)", compute='_compute_totals')
    diff_qty = fields.Float("Farq (dona)", compute='_compute_totals')
    expected_cost = fields.Monetary("Kutilgan (tannarx)", compute='_compute_totals')
    expected_sale = fields.Monetary("Kutilgan (sotuv)", compute='_compute_totals')
    surplus_cost = fields.Monetary("Ortiqcha (tannarx)", compute='_compute_totals')
    surplus_sale = fields.Monetary("Ortiqcha (sotuv)", compute='_compute_totals')
    shortage_cost = fields.Monetary("Kam (tannarx)", compute='_compute_totals')
    shortage_sale = fields.Monetary("Kam (sotuv)", compute='_compute_totals')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Yangi')) == _('Yangi'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'feliza.inventory.session') or _('Yangi')
        return super().create(vals_list)

    @api.depends('warehouse_id')
    def _compute_location_ids(self):
        Loc = self.env['stock.location']
        for rec in self:
            if rec.warehouse_id:
                view = rec.warehouse_id.view_location_id
                rec.location_ids = Loc.search([
                    ('id', 'child_of', view.id),
                    ('usage', '=', 'internal')]).ids
            else:
                rec.location_ids = False

    @api.depends('start_at', 'end_at')
    def _compute_duration(self):
        for rec in self:
            end = rec.end_at or (fields.Datetime.now()
                                 if rec.state == 'in_progress' else False)
            if rec.start_at and end:
                secs = (end - rec.start_at).total_seconds()
                h = int(secs // 3600); m = int((secs % 3600) // 60)
                rec.duration_label = ("%d soat %d daqiqa" % (h, m)
                                      if h else "%d daqiqa" % m)
            else:
                rec.duration_label = "—"

    def _compute_my_location(self):
        Cur = self.env['feliza.inventory.cursor'].sudo()
        for rec in self:
            if not isinstance(rec.id, int):  # yangi (saqlanmagan) yozuv
                rec.my_location_id = False
                continue
            c = Cur.search([('session_id', '=', rec.id),
                            ('user_id', '=', rec.env.uid)], limit=1)
            rec.my_location_id = c.location_id if c else False

    @api.depends('scan_ids.user_id', 'scan_ids.qty')
    def _compute_participants(self):
        for rec in self:
            if not isinstance(rec.id, int):  # yangi yozuvда SQL id yo'q
                rec.participants_label = "—"
                rec.scan_count = 0
                continue
            self.env.cr.execute(
                "SELECT u.id, COALESCE(SUM(sc.qty),0), COUNT(*) "
                "FROM feliza_inventory_scan sc "
                "JOIN res_users u ON u.id = sc.user_id "
                "WHERE sc.session_id = %s GROUP BY u.id "
                "ORDER BY 2 DESC", (rec.id,))
            parts = self.env.cr.fetchall()
            names = {u.id: u.display_name
                     for u in self.env['res.users'].browse([p[0] for p in parts])}
            rec.participants_label = "  |  ".join(
                "%s: %d dona" % (names.get(p[0], '?'), p[1]) for p in parts) or "—"
            rec.scan_count = sum(int(p[2]) for p in parts)

    @api.depends('scan_ids')
    def _compute_recent_scans(self):
        for rec in self:
            if not isinstance(rec.id, int):
                rec.recent_scan_ids = False
                continue
            self.env.cr.execute(
                "SELECT id FROM feliza_inventory_scan WHERE session_id=%s "
                "ORDER BY id DESC LIMIT 10", (rec.id,))
            rec.recent_scan_ids = [r[0] for r in self.env.cr.fetchall()]

    def _cursor(self):
        """Joriy foydalanuvchining shu sessiyadagi kursori (yo'q bo'lsa yaratadi).
        Bir user bir vaqtда ikki skan yuborsa unique(session,user) to'qnashuvi
        bo'lmasligi uchun savepoint bilan (birinchisi yaratadi, ikkinchisi topadi)."""
        self.ensure_one()
        Cur = self.env['feliza.inventory.cursor'].sudo()
        dom = [('session_id', '=', self.id), ('user_id', '=', self.env.uid)]
        c = Cur.search(dom, limit=1)
        if c:
            return c
        try:
            with self.env.cr.savepoint():
                return Cur.create({'session_id': self.id,
                                   'user_id': self.env.uid})
        except Exception:
            c = Cur.search(dom, limit=1)
            if c:
                return c
            raise

    @api.depends('line_ids.counted_qty', 'line_ids.expected_final',
                 'line_ids.expected_start', 'line_ids.cost_price',
                 'line_ids.sale_price', 'line_ids.product_id', 'state',
                 'expected_start_json', 'expected_total_qty',
                 'expected_total_cost', 'expected_total_sale',
                 'expected_total_types')
    def _compute_totals(self):
        """ANIQLIK (Task 5): solishtirish JAVON emas, MAHSULOT darajasida.
        Do'konда butun stok ota-lokatsiyada (onlin/Stock) turadi, javonlar
        bo'sh. Skanerlash javonlarga bo'lib boradi. Shuning uchun har javonni
        alohida solishtirsak — javon = ortiqcha, ota-Stock = kam bo'lib
        chalkashadi. Bu yerda barcha javonlarни MAHSULOT bo'yicha yig'ib,
        butun ombor KUTILGANiga solishtiramiz (1 donaga ham adashmasin)."""
        for rec in self:
            lines = rec.line_ids
            # counted/expected_final/expected_start ni MAHSULOT bo'yicha yig'amiz
            agg = {}  # pid -> {'ef','c','es','cost','sale'}
            for l in lines:
                pid = l.product_id.id
                d = agg.setdefault(pid, {'ef': 0.0, 'c': 0.0, 'es': 0.0,
                                        'cost': l.cost_price, 'sale': l.sale_price})
                d['ef'] += l.expected_final
                d['c'] += l.counted_qty
                d['es'] += l.expected_start
            rec.counted_qty = sum(d['c'] for d in agg.values())

            sur_q = sho_q = sold = 0.0
            sur_c = sur_s = sho_c = sho_s = 0.0

            if rec.state == 'done':
                # Yakunlangan: har mahsulot uchun oxirgi kutilgan (expected_final,
                # sotuvdan keyingi) — bu apply yozadigan haqiqiy holat.
                exp = exp_c = exp_s = 0.0
                for pid, d in agg.items():
                    e = d['ef']
                    c = d['c']
                    sold += max(d['es'] - d['ef'], 0.0)
                    exp += e
                    exp_c += e * d['cost']
                    exp_s += e * d['sale']
                    diff = c - e
                    if diff > 0.0001:
                        sur_q += diff; sur_c += diff * d['cost']; sur_s += diff * d['sale']
                    elif diff < -0.0001:
                        sho_q += diff; sho_c += diff * d['cost']; sho_s += diff * d['sale']
                rec.product_count = len(agg)
                rec.expected_qty = exp
                rec.expected_cost = exp_c
                rec.expected_sale = exp_s
            else:
                # Sanalyapti/tayyorlanmoqda: KUTILGAN = boshda muzlatilgan butun
                # ombor jami (mahsulot kesimida), sotuvdan chalkashmaydi.
                try:
                    snap = json.loads(rec.expected_start_json or '{}')
                except Exception:
                    snap = {}
                exp_by = {}
                for key, q in snap.items():
                    pid = int(key.split('-')[1])
                    exp_by[pid] = exp_by.get(pid, 0.0) + q
                for pid, e in exp_by.items():
                    d = agg.get(pid)
                    c = d['c'] if d else 0.0
                    cost = d['cost'] if d else 0.0
                    sale = d['sale'] if d else 0.0
                    diff = c - e
                    if diff > 0.0001:
                        sur_q += diff; sur_c += diff * cost; sur_s += diff * sale
                    elif diff < -0.0001:
                        sho_q += diff; sho_c += diff * cost; sho_s += diff * sale
                # snapshotда yo'q, lekin sanalgan (yangi) mahsulot = ortiqcha
                for pid, d in agg.items():
                    if pid not in exp_by and d['c'] > 0.0001:
                        sur_q += d['c']; sur_c += d['c'] * d['cost']; sur_s += d['c'] * d['sale']
                rec.product_count = len(exp_by) or len(agg)
                rec.expected_qty = rec.expected_total_qty
                rec.expected_cost = rec.expected_total_cost
                rec.expected_sale = rec.expected_total_sale

            rec.sold_qty = sold
            rec.diff_qty = rec.counted_qty - rec.expected_qty
            rec.surplus_qty = sur_q
            rec.shortage_qty = sho_q
            rec.surplus_cost = sur_c
            rec.surplus_sale = sur_s
            rec.shortage_cost = sho_c
            rec.shortage_sale = sho_s

    # ---- snapshot yordamchilari ----
    def _snapshot_get(self, loc_id, product_id):
        try:
            snap = json.loads(self.expected_start_json or '{}')
        except Exception:
            snap = {}
        return snap.get('%d-%d' % (loc_id, product_id), 0.0)

    def _onhand(self, loc_id, product_id):
        self.env.cr.execute(
            "SELECT COALESCE(SUM(quantity),0) FROM stock_quant "
            "WHERE location_id=%s AND product_id=%s", (loc_id, product_id))
        return self.env.cr.fetchone()[0]

    # ---- amallar ----
    def action_start(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Faqat 'Tayyorlanmoqda' holatida boshlanadi."))
        # location_ids — stored compute; ombor tuzilishi o'zgargan bo'lsa
        # (yangi javon/sub-lokatsiya qo'shilgan) eskirib qolishi mumkin.
        # Boshlashda MAJBURAN qayta hisoblaymiz — shunda barcha joriy
        # javonlar skanerlanadigan bo'ladi.
        self._compute_location_ids()
        self.flush_recordset(['location_ids'])
        if not self.location_ids:
            raise UserError(_("Bu omborда ichki joy topilmadi."))
        self.env.cr.execute(
            "SELECT location_id, product_id, COALESCE(SUM(quantity),0) "
            "FROM stock_quant WHERE location_id IN %s AND quantity != 0 "
            "GROUP BY location_id, product_id",
            (tuple(self.location_ids.ids) or (0,),))
        snap = {'%d-%d' % (r[0], r[1]): r[2] for r in self.env.cr.fetchall()}
        self.expected_start_json = json.dumps(snap)
        # Butun sklad KUTILGAN: dona + tannarx + sotuv (mahsulot kesimida)
        prod_qty = {}
        for key, q in snap.items():
            pid = int(key.split('-')[1])
            prod_qty[pid] = prod_qty.get(pid, 0.0) + q
        prods = self.env['product.product'].sudo().browse(list(prod_qty))
        pinfo = {p.id: (p.standard_price, p.list_price)
                 for p in prods if p.exists()}
        tcost = sum(q * pinfo.get(pid, (0.0, 0.0))[0]
                    for pid, q in prod_qty.items())
        tsale = sum(q * pinfo.get(pid, (0.0, 0.0))[1]
                    for pid, q in prod_qty.items())
        self.write({'state': 'in_progress',
                    'start_at': fields.Datetime.now(),
                    'current_location_id': False,
                    'expected_total_qty': sum(prod_qty.values()),
                    'expected_total_types': len(prod_qty),
                    'expected_total_cost': tcost,
                    'expected_total_sale': tsale})
        return True

    def scan_barcode(self, barcode):
        """Skanerdan chaqiriladi. Lokatsiya bo'lsa joriy joyni belgilaydi,
        tovar bo'lsa joriy joyga +1 qiladi."""
        self.ensure_one()
        if self.state != 'in_progress':
            return {'ok': False, 'message': _("Sessiya faol emas — 'Boshlash'ni bosing.")}
        code = (barcode or '').strip()
        if not code:
            return {'ok': False, 'message': _("Bo'sh barkod.")}
        Loc = self.env['stock.location'].sudo()
        loc = Loc.search([('barcode', '=', code), ('usage', '=', 'internal')], limit=1)
        if not loc:
            # Barkodsiz lokatsiyalar uchun NOM bo'yicha qidiruv — faqat shu
            # sessiya ombori ichida (chalkashmasligi uchun). QR barkod
            # o'rniga nomni (masalan "1-C") kodlagan bo'lsa ham topiladi.
            loc = Loc.search([('id', 'in', self.location_ids.ids),
                              ('name', '=', code)], limit=1)
            if not loc:
                loc = Loc.search([('id', 'in', self.location_ids.ids),
                                  ('name', '=ilike', code)], limit=1)
        cur = self._cursor()
        if loc:
            if loc.id not in self.location_ids.ids:
                return {'ok': False,
                        'message': _("Bu joy tanlangan omborga tegishli emas: %s") % loc.complete_name}
            # Joriy joy har FOYDALANUVCHI uchun ALOHIDA (kursor) — sessiya
            # (umumiy qator)ga YOZMAYMIZ: ko'p-skaner bir vaqtda yozganда
            # to'qnashmasin (REPEATABLE READ) va oddiy user ham yoza olsin.
            cur.location_id = loc.id
            return {'ok': True, 'type': 'location', 'name': loc.complete_name}
        Prod = self.env['product.product'].sudo()
        prod = Prod.search([('barcode', '=', code)], limit=1)
        if not prod:
            return {'ok': False, 'message': _("Topilmadi: %s") % code}
        if not cur.location_id:
            return {'ok': False, 'message': _("Avval LOKATSIYA barkodini skanerlang.")}
        line = self._get_or_create_line(cur.location_id.id, prod)
        # Har skan = ALOHIDA INSERT (yozuvlar to'qnashmaydi, yo'qolmaydi)
        self.env['feliza.inventory.scan'].sudo().create(
            {'line_id': line.id, 'qty': 1.0})
        self.env.cr.execute(
            "SELECT COALESCE(SUM(qty),0) FROM feliza_inventory_scan "
            "WHERE line_id=%s", (line.id,))
        counted = self.env.cr.fetchone()[0]
        return {'ok': True, 'type': 'product', 'name': prod.display_name,
                'counted': counted,
                'location': cur.location_id.complete_name}

    def _get_or_create_line(self, loc_id, prod):
        """(joy, tovar) qatorini topadi yoki yaratadi (mahsulot uchun bir marta).
        Sanash shu qatorga bog'langan INSERT-yozuvlar bilan hisoblanadi."""
        Line = self.env['feliza.inventory.line'].sudo()
        dom = [('session_id', '=', self.id), ('location_id', '=', loc_id),
               ('product_id', '=', prod.id)]
        line = Line.search(dom, limit=1)
        if line:
            return line
        try:
            with self.env.cr.savepoint():
                return Line.create({
                    'session_id': self.id, 'location_id': loc_id,
                    'product_id': prod.id,
                    'expected_start': self._snapshot_get(loc_id, prod.id),
                    'cost_price': prod.standard_price,
                    'sale_price': prod.list_price,
                })
        except Exception:
            line = Line.search(dom, limit=1)
            if line:
                return line
            raise

    def action_open_additem(self):
        """Qo'lда (skanersiz) tovar qo'shish oynasini ochadi — joy joriy
        kursordan (foydalanuvchining oxirgi joyi) olinadi."""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Sessiya 'Sanalyapti' holatida bo'lishi kerak."))
        cur = self._cursor()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Qo'lda tovar qo'shish"),
            'res_model': 'feliza.inventory.additem.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
                'default_location_id': cur.location_id.id if cur.location_id else False,
            },
        }

    def action_finish(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Faqat 'Sanalyapti' holatini yakunlash mumkin."))
        cr = self.env.cr
        loc_ids = tuple(self.location_ids.ids) or (0,)
        # BITTA so'rovda barcha joriy qoldiq (loc, product) -> qty
        cr.execute(
            "SELECT location_id, product_id, COALESCE(SUM(quantity),0) "
            "FROM stock_quant WHERE location_id IN %s "
            "GROUP BY location_id, product_id", (loc_ids,))
        onhand = {(r[0], r[1]): r[2] for r in cr.fetchall()}
        # Avval 'done' qilamiz: shunda qator hisobi muzlatilgan
        # expected_final ni ishlatadi (har qatorga alohida so'rov yubormaydi).
        self.write({'state': 'done', 'end_at': fields.Datetime.now()})
        # Sanalgan qatorlarning oxirgi kutilganini muzlatamiz
        for line in self.line_ids:
            line.expected_final = onhand.get(
                (line.location_id.id, line.product_id.id), 0.0)
        # Sanalmagan, lekin boshda qoldiq bo'lgan tovarlar = KAM (bitta batch)
        try:
            snap = json.loads(self.expected_start_json or '{}')
        except Exception:
            snap = {}
        existing = set((l.location_id.id, l.product_id.id)
                       for l in self.line_ids)
        missing = []
        for key, qty in snap.items():
            if qty <= 0:
                continue
            locid, pid = (int(x) for x in key.split('-'))
            if (locid, pid) in existing:
                continue
            missing.append((locid, pid, qty))
        if missing:
            prods = self.env['product.product'].browse([m[1] for m in missing])
            pinfo = {p.id: (p.standard_price, p.list_price)
                     for p in prods if p.exists()}
            vals = []
            for locid, pid, qty in missing:
                if pid not in pinfo:
                    continue
                cost, sale = pinfo[pid]
                vals.append({
                    'session_id': self.id, 'location_id': locid,
                    'product_id': pid,
                    'expected_start': qty,
                    'expected_final': onhand.get((locid, pid), 0.0),
                    'cost_price': cost, 'sale_price': sale,
                })
            if vals:
                self.env['feliza.inventory.line'].create(vals)
        # expected_final ni DB ga tushiramiz: "Mahsulot kesimi" SQL view'i xom
        # SQL bilan o'qiydi — bitta so'rovda ochilса ham to'g'ri ko'rinsin.
        self.env.flush_all()
        return True

    APPLY_CHUNK = 1000

    def action_apply(self):
        """Sanalgan sonlarni Odoo astatkasiga yozadi (inventory adjustment).
        Har (joy, tovar): astatka = sanalgan. Sanalmagan (kam) tovarlar 0 ga
        tushadi. Bu ongli qadam — avval hisobot ko'riladi, keyin qo'llanadi.

        TEZLIK (Task 6): har qatorда alohida search/apply/commit YO'Q. Buning
        o'rniga (1) bitta SQL bilan sanalgan (joy,tovar)->son, (2) bitta search
        bilan mavjud quantlar, (3) yo'qlarini bitta create, (4) inventory
        harakatlarини 1000 talik BATCH da qo'llash. 5000-100000 tovar uchun."""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("Avval inventarizatsiyani yakunlang."))
        if self.applied:
            raise UserError(_("Bu inventarizatsiya astatkaga allaqachon "
                              "qo'llangan."))
        cr = self.env.cr
        # 1) Sanalgan son (joy, tovar) kesimida — BITTA so'rov
        cr.execute("""
            SELECT l.location_id, l.product_id, COALESCE(SUM(sc.qty), 0)
            FROM feliza_inventory_line l
            LEFT JOIN feliza_inventory_scan sc ON sc.line_id = l.id
            WHERE l.session_id = %s
            GROUP BY l.location_id, l.product_id
        """, (self.id,))
        targets = {(r[0], r[1]): round(r[2] or 0.0, 3) for r in cr.fetchall()}
        if not targets:
            self.write({'applied': True, 'applied_at': fields.Datetime.now(),
                        'applied_by': self.env.user.id})
            return True
        loc_ids = list({k[0] for k in targets})
        pid_ids = list({k[1] for k in targets})
        Quant = self.env['stock.quant'].with_context(
            inventory_mode=True).sudo()
        # 2) Mavjud quantlar — BITTA search (keyin (joy,tovar) bo'yicha map)
        existing = Quant.search([('location_id', 'in', loc_ids),
                                 ('product_id', 'in', pid_ids)])
        qmap = {}
        for q in existing:
            qmap.setdefault((q.location_id.id, q.product_id.id), q)
        # 3) inventory_quantity o'rnatamiz; yo'qlarini bitta batch create
        to_apply = Quant.browse()
        create_vals = []
        for (loc, pid), target in targets.items():
            q = qmap.get((loc, pid))
            if q:
                if abs(q.quantity - target) < 0.001:
                    continue
                q.inventory_quantity = target
                to_apply |= q
            elif target > 0.0001:
                create_vals.append({'product_id': pid, 'location_id': loc,
                                    'inventory_quantity': target})
        if create_vals:
            to_apply |= Quant.create(create_vals)
        # 4) Inventory harakatlarini BATCH qo'llash (1000 talik bo'laklar)
        ids = to_apply.ids
        for i in range(0, len(ids), self.APPLY_CHUNK):
            Quant.browse(ids[i:i + self.APPLY_CHUNK]).action_apply_inventory()
            cr.commit()
        self.write({'applied': True, 'applied_at': fields.Datetime.now(),
                    'applied_by': self.env.user.id})
        return True

    def action_view_products(self):
        """Mahsulot kesimidagi aniq solishtiruvni USTMA-UST OYNADA (dialog)
        ochadi — tepada qidiruv (mahsulot/barkod/holat), ostida ro'yxat +
        inline son tuzatish. Form ustida turadi, bo'sh joy yo'q."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("🔍 Qidiruv / tuzatish — %s") % self.name,
            'res_model': 'feliza.inventory.product',
            'view_mode': 'list',
            'target': 'new',
            'domain': [('session_id', '=', self.id)],
            'context': {'search_default_f_diff': 1, 'create': False,
                        'delete': False},
        }

    def action_view_scans(self):
        """Skan tarixini to'liq ro'yxatда ochadi — ishtirokchi (Kim), joy,
        tovar bo'yicha FILTR/GURUHLASH mumkin."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Skan tarixi — %s") % self.name,
            'res_model': 'feliza.inventory.scan',
            'view_mode': 'list',
            'domain': [('session_id', '=', self.id)],
            'context': {'search_default_group_user': 1},
        }

    def _export_xlsx(self, status):
        """Mahsulot kesimini Excel (xlsx) ga chiqaradi. status='shortage' (kam),
        'surplus' (ko'p) yoki False (barchasi)."""
        self.ensure_one()
        import io
        import base64
        import xlsxwriter
        dom = [('session_id', '=', self.id)]
        if status:
            dom.append(('status', '=', status))
        rows = self.env['feliza.inventory.product'].sudo().search(
            dom, order='diff_cost')
        out = io.BytesIO()
        wb = xlsxwriter.Workbook(out, {'in_memory': True})
        ws = wb.add_worksheet((status or 'barchasi')[:31])
        bold = wb.add_format({'bold': True, 'bg_color': '#DDDDDD', 'border': 1})
        num = wb.add_format({'num_format': '#,##0'})
        money = wb.add_format({'num_format': '#,##0'})
        headers = ["Tovar", "Artikul", "Barkod", "Rang/O'lcham", "Javonlar",
                   "Kutilgan", "Sanalgan", "Sotilgan (davomida)", "Farq",
                   "Farq (tannarx)", "Farq (sotuv)"]
        widths = [34, 12, 16, 16, 22, 10, 10, 16, 10, 14, 14]
        for c, h in enumerate(headers):
            ws.write(0, c, h, bold)
            ws.set_column(c, c, widths[c])
        ws.freeze_panes(1, 0)
        r = 1
        for p in rows:
            prod = p.product_id
            vinfo = ", ".join(prod.product_template_attribute_value_ids.mapped('name'))
            ws.write(r, 0, prod.display_name or '')
            ws.write(r, 1, prod.default_code or '')
            ws.write(r, 2, prod.barcode or '')
            ws.write(r, 3, vinfo)
            ws.write(r, 4, p.location_names or '')
            ws.write(r, 5, p.expected_qty, num)
            ws.write(r, 6, p.counted_qty, num)
            ws.write(r, 7, p.sold_qty, num)
            ws.write(r, 8, p.diff_qty, num)
            ws.write(r, 9, p.diff_cost, money)
            ws.write(r, 10, p.diff_sale, money)
            r += 1
        wb.close()
        data = out.getvalue()
        tag = {'shortage': 'KAM', 'surplus': 'KOP'}.get(status, 'BARCHASI')
        att = self.env['ir.attachment'].create({
            'name': "%s_%s.xlsx" % (self.name.replace('/', '_'), tag),
            'type': 'binary',
            'datas': base64.b64encode(data),
            'res_model': 'feliza.inventory.session',
            'res_id': self.id,
            'mimetype': ('application/vnd.openxmlformats-officedocument.'
                         'spreadsheetml.sheet'),
        })
        return {'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=true' % att.id,
                'target': 'self'}

    def action_export_shortage(self):
        return self._export_xlsx('shortage')

    def action_export_surplus(self):
        return self._export_xlsx('surplus')

    def action_export_all(self):
        return self._export_xlsx(False)

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset(self):
        if self.applied:
            raise UserError(_("Astatkaga qo'llangan inventarizatsiyani qayta "
                              "boshlab bo'lmaydi."))
        self.write({'state': 'draft', 'start_at': False, 'end_at': False,
                    'current_location_id': False, 'expected_start_json': False,
                    'expected_total_qty': 0.0, 'expected_total_types': 0,
                    'expected_total_cost': 0.0, 'expected_total_sale': 0.0})
        self.line_ids.unlink()
