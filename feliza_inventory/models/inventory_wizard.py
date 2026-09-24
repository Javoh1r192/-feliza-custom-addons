# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FelizaInventoryCountWizard(models.TransientModel):
    """Qo'lда sanoqni tuzatish (Task 3). Append-only'ni buzmaydi: farqni
    (yangi - joriy) 'qo'lда tuzatish' skani sifatida qo'shadi — audit saqlanadi."""
    _name = 'feliza.inventory.count.wizard'
    _description = "Sanoqni qo'lda tuzatish"

    line_id = fields.Many2one('feliza.inventory.line', required=True)
    product_id = fields.Many2one(related='line_id.product_id', readonly=True)
    location_id = fields.Many2one(related='line_id.location_id', readonly=True)
    current_counted = fields.Float("Hozirgi sanoq", readonly=True,
                                   digits='Product Unit of Measure')
    new_counted = fields.Float("Yangi sanoq", digits='Product Unit of Measure')
    reason = fields.Char("Sabab")

    def action_confirm(self):
        self.ensure_one()
        line = self.line_id
        if line.session_id.applied:
            raise UserError(_("Astatkaga qo'llangan sessiyani tahrirlab bo'lmaydi."))
        delta = round(self.new_counted - line.counted_qty, 3)
        if abs(delta) > 0.0001:
            is_del = round(self.new_counted or 0.0, 3) == 0 and line.counted_qty > 0
            self.env['feliza.inventory.scan'].sudo().create({
                'line_id': line.id, 'qty': delta, 'is_manual': True,
                'is_delete': is_del,
            })
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}


class FelizaInventoryAddItemWizard(models.TransientModel):
    """Qo'lда (skanersiz) tovar qo'shish. Artikul/nom/barkod bo'yicha qidiradi,
    shu artikulга tegishli variantlar chiqadi — kerakligini belgilab, sonini
    kiritib qo'shadi. Har qo'shilgan tovar 'qo'lда' skan sifatida yoziladi."""
    _name = 'feliza.inventory.additem.wizard'
    _description = "Inventarizatsiya — qo'lda tovar qo'shish"

    session_id = fields.Many2one('feliza.inventory.session', required=True)
    location_id = fields.Many2one(
        'stock.location', "Joy (javon)", required=True,
        help="Tovarlar shu joyga qo'shiladi.")
    allowed_location_ids = fields.Many2many(
        'stock.location', compute='_compute_allowed_locations')
    query = fields.Char("Qidiruv (artikul / nom / barkod)")
    line_ids = fields.One2many('feliza.inventory.additem.line', 'wizard_id',
                               "Topilgan tovarlar")

    @api.depends('session_id')
    def _compute_allowed_locations(self):
        for w in self:
            w.allowed_location_ids = w.session_id.location_ids

    @api.onchange('query')
    def _onchange_query(self):
        self.line_ids = [(5, 0, 0)]
        q = (self.query or '').strip()
        if len(q) < 2:
            return
        Product = self.env['product.product'].sudo()
        prods = Product.search([
            '&', ('active', '=', True),
            '|', '|', ('default_code', 'ilike', q),
            ('barcode', 'ilike', q), ('name', 'ilike', q),
        ], limit=200)
        self.line_ids = [(0, 0, {'product_id': p.id, 'qty': 0.0,
                                 'selected': False}) for p in prods]

    def action_add(self):
        self.ensure_one()
        if self.session_id.state != 'in_progress':
            raise UserError(_("Sessiya 'Sanalyapti' holatida bo'lishi kerak."))
        if not self.location_id:
            raise UserError(_("Joyni (javonni) tanlang."))
        Scan = self.env['feliza.inventory.scan'].sudo()
        chosen = self.line_ids.filtered(lambda l: l.selected and l.qty > 0)
        if not chosen:
            raise UserError(_("Kamida bitta tovarni belgilang va sonini kiriting."))
        added = 0
        for wl in chosen:
            line = self.session_id._get_or_create_line(
                self.location_id.id, wl.product_id)
            Scan.create({'line_id': line.id, 'qty': wl.qty, 'is_manual': True})
            added += 1
        self.env.flush_all()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _("Qo'shildi"),
                       'message': _("%s tovar qo'shildi.") % added,
                       'type': 'success', 'sticky': False,
                       'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'}},
        }


class FelizaInventoryAddItemLine(models.TransientModel):
    _name = 'feliza.inventory.additem.line'
    _description = "Inventarizatsiya — qo'shiladigan tovar qatori"

    wizard_id = fields.Many2one('feliza.inventory.additem.wizard',
                                required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', "Tovar", required=True)
    default_code = fields.Char("Artikul", related='product_id.default_code')
    barcode = fields.Char("Barkod", related='product_id.barcode')
    variant_info = fields.Char("Rang / O'lcham", compute='_compute_variant')
    selected = fields.Boolean("Belgilash")
    qty = fields.Float("Soni", digits='Product Unit of Measure')
    # Shu sessiyaда bu tovar ALLAQACHON qancha sanalgani ("ro'yxatда bor").
    current_counted = fields.Float(
        "Sanalgan (joriy)", compute='_compute_current_counted',
        digits='Product Unit of Measure')

    @api.depends('product_id')
    def _compute_variant(self):
        for rec in self:
            vals = rec.product_id.product_template_attribute_value_ids
            rec.variant_info = ", ".join(v.name for v in vals) if vals else ""

    @api.depends('product_id', 'wizard_id.session_id')
    def _compute_current_counted(self):
        """Har qatorда shu tovar sessiyaда hozircha necha dona sanalganини
        ko'rsatadi — skanerlangan (yoki qo'lда qo'shilgan) bo'lsa darhol
        ko'rinadi, ya'ni 'ro'yxatда bor' degani."""
        Line = self.env['feliza.inventory.line'].sudo()
        # Bitta search bilan — sessiya bo'yicha kerakli tovarlar
        want = {}
        for rec in self:
            sess = rec.wizard_id.session_id
            if sess and rec.product_id:
                want.setdefault(sess.id, set()).add(rec.product_id.id)
        totals = {}
        for sid, pids in want.items():
            for ln in Line.search([('session_id', '=', sid),
                                   ('product_id', 'in', list(pids))]):
                key = (sid, ln.product_id.id)
                totals[key] = totals.get(key, 0.0) + ln.counted_qty
        for rec in self:
            sess = rec.wizard_id.session_id
            rec.current_counted = totals.get(
                (sess.id, rec.product_id.id), 0.0) if sess and rec.product_id else 0.0


class FelizaInventoryProductCountWizard(models.TransientModel):
    """MAHSULOT darajasida sanoqni qo'lда tuzatish (Mahsulot kesimidan).
    Mahsulotning butun sessiyadagi sanog'ini yangi songa keltiradi — farqni
    eng ko'p sanalgan javon qatoriga 'qo'lда tuzatish' skani qilib qo'shadi."""
    _name = 'feliza.inventory.pcount.wizard'
    _description = "Mahsulot sanog'ini qo'lda tuzatish"

    session_id = fields.Many2one('feliza.inventory.session', required=True)
    product_id = fields.Many2one('product.product', "Tovar", readonly=True)
    current_counted = fields.Float("Hozirgi sanoq", readonly=True,
                                   digits='Product Unit of Measure')
    new_counted = fields.Float("Yangi sanoq", digits='Product Unit of Measure')

    def action_confirm(self):
        self.ensure_one()
        if self.session_id.applied:
            raise UserError(_("Astatkaga qo'llangan sessiyani tahrirlab bo'lmaydi."))
        Line = self.env['feliza.inventory.line'].sudo()
        lines = Line.search([('session_id', '=', self.session_id.id),
                             ('product_id', '=', self.product_id.id)])
        if not lines:
            raise UserError(_("Bu mahsulot uchun qator topilmadi."))
        current = sum(lines.mapped('counted_qty'))
        delta = round((self.new_counted or 0.0) - current, 3)
        if abs(delta) > 0.0001:
            # farqni eng ko'p sanalgan (bo'lmasa birinchi) javon qatoriga yozamiz
            target = lines.sorted(lambda l: l.counted_qty, reverse=True)[:1]
            is_del = round(self.new_counted or 0.0, 3) == 0 and current > 0
            self.env['feliza.inventory.scan'].sudo().create({
                'line_id': target.id, 'qty': delta, 'is_manual': True,
                'is_delete': is_del,
            })
            self.env.flush_all()  # SQL view (mahsulot kesimi) darhol yangilansin
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}


class FelizaInventoryLocMoveWizard(models.TransientModel):
    """Mahsulotni boshqa JOYGA (javonga) ko'chirish — noto'g'ri javonga
    skanerlangan tovarni to'g'rilaydi. Append-only: eski javon(lar)dan
    chiqarib (qty=-joriy), yangi javonga qo'shadi (qty=+joriy). Sof son
    o'zgarmaydi, faqat JOY o'zgaradi. Yangi joy ro'yxati = SHU omborning
    javonlari (session.location_ids)."""
    _name = 'feliza.inventory.locmove.wizard'
    _description = "Inventarizatsiya — joyni o'zgartirish"

    session_id = fields.Many2one('feliza.inventory.session', required=True)
    product_id = fields.Many2one('product.product', "Tovar", readonly=True)
    current_location = fields.Char("Hozirgi joy", readonly=True)
    counted_qty = fields.Float("Sanalgan (dona)", readonly=True,
                               digits='Product Unit of Measure')
    allowed_location_ids = fields.Many2many(
        'stock.location', compute='_compute_allowed')
    new_location_id = fields.Many2one(
        'stock.location', "Yangi joy (javon)", required=True,
        help="Shu omborning javoni — tovar shu joyga ko'chiriladi.")

    @api.depends('session_id')
    def _compute_allowed(self):
        for w in self:
            w.allowed_location_ids = w.session_id.location_ids

    def action_confirm(self):
        self.ensure_one()
        session = self.session_id
        if session.applied:
            raise UserError(_("Astatkaga qo'llangan sessiyani o'zgartirib "
                              "bo'lmaydi."))
        if not self.new_location_id:
            raise UserError(_("Yangi joyni (javonni) tanlang."))
        Line = self.env['feliza.inventory.line'].sudo()
        Scan = self.env['feliza.inventory.scan'].sudo()
        new_line = session._get_or_create_line(
            self.new_location_id.id, self.product_id)
        old_lines = Line.search([('session_id', '=', session.id),
                                 ('product_id', '=', self.product_id.id)])
        for line in old_lines:
            if line.id == new_line.id:
                continue
            cur = line.counted_qty
            if abs(cur) > 0.0001:
                # eski joydan chiqarib, yangi joyga qo'shamiz (ko'chirish)
                Scan.create({'line_id': line.id, 'qty': -cur,
                             'is_manual': True})
                Scan.create({'line_id': new_line.id, 'qty': cur,
                             'is_manual': True})
        self.env.flush_all()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}


class FelizaInventoryBulkLocWizard(models.TransientModel):
    """KO'P tovarni bitta JOYGA (javonga) biriktirish + sonini tuzatish — mahsulot
    kesimidan bir nechta tovar belgilanadi, hammasi tanlangan joyga o'tkaziladi va
    (ixtiyoriy) har birining SONI o'zgartiriladi. Append-only: har tovar uchun eski
    javon(lar)dan chiqarib (qty=-joriy), yangi javonga qo'shadi (qty=+joriy) —
    keyin yangi son bilan joriy son farqini yangi javonga skan qilib qo'shadi.
    Hech narsa o'chmaydi, skan tarixi to'liq saqlanadi."""
    _name = 'feliza.inventory.bulkloc.wizard'
    _description = "Inventarizatsiya — tanlanganlarni joyga biriktirish"

    session_id = fields.Many2one('feliza.inventory.session', required=True)
    line_ids = fields.One2many('feliza.inventory.bulkloc.line', 'wizard_id',
                               "Ko'chiriladigan tovarlar")
    product_count = fields.Integer("Tovarlar soni", compute='_compute_count')
    allowed_location_ids = fields.Many2many(
        'stock.location', compute='_compute_allowed')
    # required emas (model darajasi) — wizard joy tanlanmasdan yaratiladi;
    # majburiylik view'da (required="1") + action_confirm tekshiruvida.
    new_location_id = fields.Many2one(
        'stock.location', "Joy (javon)",
        help="Tanlangan tovarlar shu javonga biriktiriladi (ko'chiriladi).")

    @api.depends('line_ids')
    def _compute_count(self):
        for w in self:
            w.product_count = len(w.line_ids)

    @api.depends('session_id')
    def _compute_allowed(self):
        for w in self:
            w.allowed_location_ids = w.session_id.location_ids

    def action_confirm(self):
        self.ensure_one()
        session = self.session_id
        if session.applied:
            raise UserError(_("Astatkaga qo'llangan sessiyani o'zgartirib "
                              "bo'lmaydi."))
        if not self.new_location_id:
            raise UserError(_("Joyni (javonni) tanlang."))
        if self.new_location_id.id not in session.location_ids.ids:
            raise UserError(_("Tanlangan joy shu sessiya omboriga tegishli emas."))
        if not self.line_ids:
            raise UserError(_("Tovarlar tanlanmagan."))
        Line = self.env['feliza.inventory.line'].sudo()
        Scan = self.env['feliza.inventory.scan'].sudo()
        moved = 0
        changed = 0
        for wl in self.line_ids:
            prod = wl.product_id
            new_qty = round(wl.new_qty or 0.0, 3)
            new_line = session._get_or_create_line(self.new_location_id.id, prod)
            all_lines = Line.search([('session_id', '=', session.id),
                                     ('product_id', '=', prod.id)])
            # 1) JOY: hammasini yangi javonga jamlaymiz (ko'chirish, sof=0)
            # MUHIM: total ni ko'chirishdan OLDIN hisoblaymiz. Aks holda new_line
            # (agar mavjud bo'lsa) siklda ko'chirilgandan keyin qo'shilib, soni
            # IKKI MARTA sanaladi -> total shishadi -> delta manfiy -> 0 ga tushadi.
            total = sum(all_lines.mapped('counted_qty'))
            for line in all_lines:
                if line.id == new_line.id:
                    continue
                cur = line.counted_qty
                if abs(cur) > 0.0001:
                    Scan.create({'line_id': line.id, 'qty': -cur,
                                 'is_manual': True})
                    Scan.create({'line_id': new_line.id, 'qty': cur,
                                 'is_manual': True})
            if len(all_lines) > 1:
                moved += 1
            # 2) SON: joriy jami (total) -> new_qty ga keltiramiz (farq skani)
            delta = round(new_qty - total, 3)
            if abs(delta) > 0.0001:
                is_del = new_qty == 0 and total > 0
                Scan.create({'line_id': new_line.id, 'qty': delta,
                             'is_manual': True, 'is_delete': is_del})
                changed += 1
        self.env.flush_all()
        msg = _("%s tovar '%s' joyiga biriktirildi") \
            % (len(self.line_ids), self.new_location_id.complete_name or '')
        if changed:
            msg += _("; %s tovarning soni o'zgartirildi") % changed
        msg += "."
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _("Bajarildi"), 'message': msg,
                'type': 'success', 'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }


class FelizaInventoryBulkLocLine(models.TransientModel):
    """Joyga biriktirish oynasidagi bitta tovar qatori — joriy son ko'rsatiladi,
    yangi son (ixtiyoriy) kiritiladi."""
    _name = 'feliza.inventory.bulkloc.line'
    _description = "Inventarizatsiya — joyga biriktirish qatori"

    wizard_id = fields.Many2one('feliza.inventory.bulkloc.wizard',
                                required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', "Tovar", required=True,
                                 readonly=True)
    default_code = fields.Char("Artikul", related='product_id.default_code')
    barcode = fields.Char("Barkod", related='product_id.barcode')
    current_counted = fields.Float("Sanalgan (joriy)", readonly=True,
                                   digits='Product Unit of Measure')
    new_qty = fields.Float("Yangi son", digits='Product Unit of Measure')
