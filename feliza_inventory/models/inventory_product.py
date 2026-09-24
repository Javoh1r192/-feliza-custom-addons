# -*- coding: utf-8 -*-
from odoo import _, fields, models, tools
from odoo.exceptions import UserError


class FelizaInventoryProduct(models.Model):
    """Inventarizatsiya sessiyasining MAHSULOT kesimidagi ANIQ solishtirish.
    Javonlarни (joylarни) mahsulot bo'yicha birlashtiradi — do'konда stok
    ota-lokatsiyada turib, sanash javonlarga bo'linsa ham, bu yerда tovar
    bo'yicha bitta qator: kutilgan (butun ombor) vs sanalgan (barcha javon).
    SQL view — skanerlashga yozuv yuki qo'shmaydi, guruhlash/saralash ishlaydi."""
    _name = 'feliza.inventory.product'
    _description = "Inventarizatsiya — mahsulot kesimi"
    _auto = False
    _order = 'diff_cost'

    session_id = fields.Many2one('feliza.inventory.session', "Sessiya",
                                 readonly=True, index=True)
    applied = fields.Boolean(related='session_id.applied')
    product_id = fields.Many2one('product.product', "Tovar", readonly=True)
    barcode = fields.Char("Barkod", related='product_id.barcode')
    location_names = fields.Char("Javonlar", readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    expected_qty = fields.Float("Kutilgan", readonly=True,
                                digits='Product Unit of Measure')
    counted_qty = fields.Float("Sanalgan", readonly=True,
                               digits='Product Unit of Measure')
    # Inline tahrir (popup yo'q): sanalganni to'g'ridan-to'g'ri o'zgartirish.
    # SQL view — shuning uchun store=False computed+inverse. Yozilganda farqni
    # eng ko'p sanalgan javon qatoriga "qo'lda tuzatish" skani qilib qo'yadi.
    counted_edit = fields.Float(
        "Sanalgan", compute='_compute_counted_edit',
        inverse='_inverse_counted_edit', store=False, readonly=False,
        digits='Product Unit of Measure')
    sold_qty = fields.Float("Sotilgan (davomida)", readonly=True,
                            digits='Product Unit of Measure')
    diff_qty = fields.Float("Farq", readonly=True,
                            digits='Product Unit of Measure')
    cost_price = fields.Float("Tannarx", readonly=True)
    sale_price = fields.Float("Sotuv narxi", readonly=True)
    diff_cost = fields.Monetary("Farq (tannarx)", readonly=True)
    diff_sale = fields.Monetary("Farq (sotuv)", readonly=True)
    status = fields.Selection([
        ('ok', "To'g'ri"), ('surplus', "Ortiqcha"), ('shortage', "Kam"),
    ], "Holat", readonly=True)
    # Oxirgi skan (eng katta scan id) — ro'yxatni "yangi skan tepada" tartibda
    # ko'rsatish uchun. Mavjud tovar qayta skanlanganда ham u tepaga chiqadi.
    last_scan_id = fields.Integer("Oxirgi skan", readonly=True)

    def action_edit_count(self):
        """Eski popup (prod eski view uchun saqlanadi). Yangi view inline
        widget (action_set_counted) ishlatadi."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Sanoqni tuzatish — %s") % (self.product_id.display_name or ''),
            'res_model': 'feliza.inventory.pcount.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.session_id.id,
                'default_product_id': self.product_id.id,
                'default_current_counted': self.counted_qty,
                'default_new_counted': self.counted_qty,
            },
        }

    def _compute_counted_edit(self):
        for rec in self:
            rec.counted_edit = rec.counted_qty

    def _inverse_counted_edit(self):
        for rec in self:
            if isinstance(rec.id, int):
                rec.action_set_counted(rec.counted_edit)

    def action_set_counted(self, new_value):
        """Mahsulotning butun sessiyadagi sanog'ini yangi songa keltiradi —
        farqni eng ko'p sanalgan javon qatoriga 'qo'lda tuzatish' skani qilib
        qo'shadi (append-only). Popup KERAK EMAS — inline widget chaqiradi,
        darhol saqlanadi."""
        self.ensure_one()
        Line = self.env['feliza.inventory.line'].sudo()
        Scan = self.env['feliza.inventory.scan'].sudo()
        session = self.session_id
        if session.applied:
            raise UserError(_("Astatkaga qo'llangan sessiyani o'zgartirib "
                              "bo'lmaydi."))
        lines = Line.search([('session_id', '=', session.id),
                             ('product_id', '=', self.product_id.id)])
        if not lines:
            return False
        current = sum(lines.mapped('counted_qty'))
        delta = round((new_value or 0.0) - current, 3)
        if abs(delta) > 0.0001:
            target = lines.sorted(lambda l: l.counted_qty, reverse=True)[:1]
            # 0 ga tushirilsa — "o'chirildi" audit yozuvi.
            is_del = round(new_value or 0.0, 3) == 0 and current > 0
            Scan.create({'line_id': target.id, 'qty': delta,
                         'is_manual': True, 'is_delete': is_del})
            self.env.flush_all()  # SQL view darhol yangilansin
        return True

    def action_edit_location(self):
        """Tovarni boshqa JOYGA (javonga) ko'chirish oynasini ochadi —
        shu omborning javonlari orasidan qidiruvli tanlash."""
        self.ensure_one()
        if self.session_id.applied:
            raise UserError(_("Astatkaga qo'llangan sessiyani o'zgartirib "
                              "bo'lmaydi."))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Joyni o'zgartirish — %s")
                    % (self.product_id.display_name or ''),
            'res_model': 'feliza.inventory.locmove.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_session_id': self.session_id.id,
                'default_product_id': self.product_id.id,
                'default_current_location': self.location_names or '',
                'default_counted_qty': self.counted_qty,
            },
        }

    def action_bulk_zero(self):
        """Tanlangan tovarlarni 0 qiladi (noto'g'ri sanalganlarni o'chirish).
        Append-only: har biriga kompensatsiya skani (qty=-joriy, is_delete=True)
        — Skan tarixida 'o'chirildi' bo'lib SAQLANADI. List <header> tugmasi
        orqali chaqiriladi -> DIALOGda ham ishlaydi (Действия menyusi shart emas)."""
        Scan = self.env['feliza.inventory.scan'].sudo()
        Line = self.env['feliza.inventory.line'].sudo()
        zeroed = 0
        skipped = 0
        for rec in self:
            session = rec.session_id
            if not session:
                continue
            if session.applied:
                skipped += 1
                continue
            lines = Line.search([('session_id', '=', session.id),
                                 ('product_id', '=', rec.product_id.id)])
            for line in lines:
                cur = line.counted_qty
                if abs(cur) > 0.0001:
                    Scan.create({'line_id': line.id, 'qty': -cur,
                                 'is_manual': True, 'is_delete': True})
                    zeroed += 1
        self.env.flush_all()
        msg = _("%s tovar 0 qilindi (o'chirildi). Qayta skanerlash mumkin.") \
            % zeroed
        if skipped:
            msg += _(" (%s applied sessiya o'tkazildi)") % skipped
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _("Bajarildi"), 'message': msg,
                'type': 'success', 'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def action_bulk_set_location(self):
        """Tanlangan tovarlarni bitta JOYGA (javonga) biriktirish oynasini
        ochadi — joy tanlanadi, hammasi o'sha javonga ko'chiriladi (append-only,
        sof son o'zgarmaydi). List <header> tugmasi orqali chaqiriladi."""
        recs = self.filtered(lambda r: r.session_id and not r.session_id.applied)
        if not recs:
            raise UserError(_("Tanlangan tovar yo'q yoki sessiya astatkaga "
                              "qo'llangan (o'zgartirib bo'lmaydi)."))
        sessions = recs.mapped('session_id')
        if len(sessions) > 1:
            raise UserError(_("Tanlangan tovarlar bitta sessiyaga tegishli "
                              "bo'lishi kerak."))
        line_vals = []
        seen = set()
        for r in recs:
            if r.product_id.id in seen:
                continue
            seen.add(r.product_id.id)
            line_vals.append((0, 0, {
                'product_id': r.product_id.id,
                'current_counted': r.counted_qty,
                'new_qty': r.counted_qty,
            }))
        wiz = self.env['feliza.inventory.bulkloc.wizard'].create({
            'session_id': sessions.id,
            'line_ids': line_vals,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _("Joyga biriktirish (%s tovar)") % len(line_vals),
            'res_model': 'feliza.inventory.bulkloc.wizard',
            'res_id': wiz.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Har (sessiya, mahsulot) uchun bitta qator. Kutilgan: 'done' bo'lsa
        # expected_final (sotuvdan keyingi haqiqiy), aks holda expected_start.
        exp = ("SUM(CASE WHEN s.state='done' THEN l.expected_final "
               "ELSE l.expected_start END)")
        cnt = "COALESCE(SUM(sc.cnt),0)"
        diff = "(%s - %s)" % (cnt, exp)
        # Sotilgan (davomida) = boshdagi kutilgan - oxirgi kutilgan (sotuv/chiqim).
        # s.state SUM ichida — aks holда GROUP BY talab qilinadi.
        sold = ("GREATEST(SUM(CASE WHEN s.state='done' "
                "THEN l.expected_start - l.expected_final ELSE 0 END), 0)")
        self.env.cr.execute("""
            CREATE VIEW {table} AS (
              SELECT
                MIN(l.id)              AS id,
                l.session_id          AS session_id,
                l.product_id          AS product_id,
                s.company_id          AS company_id,
                c.currency_id         AS currency_id,
                MAX(l.cost_price)     AS cost_price,
                MAX(l.sale_price)     AS sale_price,
                {exp}                 AS expected_qty,
                {cnt}                 AS counted_qty,
                COALESCE(MAX(sc.last_scan), 0) AS last_scan_id,
                {sold}                AS sold_qty,
                {diff}                AS diff_qty,
                {diff} * MAX(l.cost_price) AS diff_cost,
                {diff} * MAX(l.sale_price) AS diff_sale,
                string_agg(DISTINCT loc.complete_name, ', ')
                    FILTER (WHERE COALESCE(sc.cnt, 0) > 0) AS location_names,
                CASE WHEN {diff} >  0.0001 THEN 'surplus'
                     WHEN {diff} < -0.0001 THEN 'shortage'
                     ELSE 'ok' END    AS status
              FROM feliza_inventory_line l
              JOIN feliza_inventory_session s ON s.id = l.session_id
              JOIN res_company c ON c.id = s.company_id
              LEFT JOIN stock_location loc ON loc.id = l.location_id
              LEFT JOIN (
                SELECT line_id, SUM(qty) AS cnt, MAX(id) AS last_scan
                FROM feliza_inventory_scan GROUP BY line_id
              ) sc ON sc.line_id = l.id
              GROUP BY l.session_id, l.product_id, s.company_id, c.currency_id
            )
        """.format(table=self._table, exp=exp, cnt=cnt, diff=diff, sold=sold))
