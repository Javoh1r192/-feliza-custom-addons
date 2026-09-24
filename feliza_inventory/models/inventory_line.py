# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FelizaInventoryLine(models.Model):
    _name = 'feliza.inventory.line'
    _description = "Inventarizatsiya qatori"
    _order = 'location_id, id'

    _uniq_session_location_product = models.Constraint(
        'unique(session_id, location_id, product_id)',
        "Bir sessiyada bir (joy, tovar) uchun faqat bitta qator bo'ladi.",
    )

    session_id = fields.Many2one('feliza.inventory.session', required=True,
                                 ondelete='cascade', index=True)
    state = fields.Selection(related='session_id.state', store=True)
    applied = fields.Boolean(related='session_id.applied')
    company_id = fields.Many2one(related='session_id.company_id', store=True)
    currency_id = fields.Many2one(related='session_id.currency_id')
    location_id = fields.Many2one('stock.location', "Joy", required=True)
    product_id = fields.Many2one('product.product', "Tovar", required=True,
                                 index=True)
    barcode = fields.Char("Barkod", related='product_id.barcode')
    expected_start = fields.Float("Kutilgan (boshda)", digits='Product Unit of Measure')
    expected_final = fields.Float("Kutilgan (oxirida)", digits='Product Unit of Measure')
    scan_ids = fields.One2many('feliza.inventory.scan', 'line_id', "Skanlar")
    counted_qty = fields.Float("Sanalgan", compute='_compute_counted',
                               inverse='_inverse_counted', readonly=False,
                               digits='Product Unit of Measure')
    cost_price = fields.Float("Tannarx")
    sale_price = fields.Float("Sotuv narxi")

    expected_show = fields.Float("Kutilgan", compute='_compute_vals',
                                 digits='Product Unit of Measure')
    sold_during = fields.Float("Sotilgan (davomida)", compute='_compute_vals',
                               digits='Product Unit of Measure')
    diff_qty = fields.Float("Farq", compute='_compute_vals',
                            digits='Product Unit of Measure')
    diff_cost = fields.Monetary("Farq (tannarx)", compute='_compute_vals')
    diff_sale = fields.Monetary("Farq (sotuv)", compute='_compute_vals')
    status = fields.Selection([
        ('ok', "To'g'ri"), ('surplus', "Ortiqcha"), ('shortage', "Kam"),
    ], compute='_compute_vals')

    def _onhand(self, loc_id, product_id):
        self.env.cr.execute(
            "SELECT COALESCE(SUM(quantity),0) FROM stock_quant "
            "WHERE location_id=%s AND product_id=%s", (loc_id, product_id))
        return self.env.cr.fetchone()[0]

    def action_edit_count(self):
        """Sanoqni qo'lда tuzatish oynasini ochadi (Task 3)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Sanoqni tuzatish"),
            'res_model': 'feliza.inventory.count.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_current_counted': self.counted_qty,
                'default_new_counted': self.counted_qty,
            },
        }

    def action_set_counted(self, new_value):
        """Javon qatori sanog'ini yangi songa keltiradi (inline widget, avto-
        saqlash). Farqni 'qo'lda tuzatish' skani qilib qo'shadi (append-only)."""
        self.ensure_one()
        if self.session_id.applied:
            raise UserError(_("Astatkaga qo'llangan sessiyani o'zgartirib "
                              "bo'lmaydi."))
        self.env.cr.execute(
            "SELECT COALESCE(SUM(qty),0) FROM feliza_inventory_scan "
            "WHERE line_id=%s", (self.id,))
        current = self.env.cr.fetchone()[0]
        delta = round((new_value or 0.0) - current, 3)
        if abs(delta) > 0.0001:
            self.env['feliza.inventory.scan'].sudo().create({
                'line_id': self.id, 'qty': delta, 'is_manual': True})
            self.env.flush_all()
        return True

    @api.depends('scan_ids.qty')
    def _compute_counted(self):
        ids = [i for i in self.ids]
        totals = {}
        if ids:
            self.env.cr.execute(
                "SELECT line_id, COALESCE(SUM(qty),0) FROM feliza_inventory_scan "
                "WHERE line_id IN %s GROUP BY line_id", (tuple(ids),))
            totals = dict(self.env.cr.fetchall())
        for line in self:
            line.counted_qty = totals.get(line.id, 0.0)

    def _inverse_counted(self):
        """Sanalganni QO'LDA (inline) o'zgartirish: farqni 'qo'lda tuzatish'
        skani sifatida qo'shadi (append-only saqlanadi). KIM o'zgartirgani
        scan.user_id ga yoziladi — skan tarixida ko'rinadi."""
        Scan = self.env['feliza.inventory.scan']
        for line in self:
            if not isinstance(line.id, int):
                continue
            if line.session_id.applied:
                raise UserError(_("Astatkaga qo'llangan sessiyani o'zgartirib "
                                  "bo'lmaydi."))
            self.env.cr.execute(
                "SELECT COALESCE(SUM(qty),0) FROM feliza_inventory_scan "
                "WHERE line_id=%s", (line.id,))
            current = self.env.cr.fetchone()[0]
            delta = round((line.counted_qty or 0.0) - current, 3)
            if abs(delta) > 0.0001:
                Scan.create({'line_id': line.id, 'qty': delta,
                             'is_manual': True})

    @api.depends('counted_qty', 'expected_start', 'expected_final',
                 'cost_price', 'sale_price', 'state',
                 'location_id', 'product_id')
    def _compute_vals(self):
        for line in self:
            if line.state == 'done':
                exp = line.expected_final
            elif line.state == 'in_progress' and line.location_id and line.product_id:
                exp = line._onhand(line.location_id.id, line.product_id.id)
            else:
                exp = line.expected_start
            line.expected_show = exp
            line.sold_during = max(line.expected_start - exp, 0.0)
            diff = line.counted_qty - exp
            line.diff_qty = diff
            line.diff_cost = diff * line.cost_price
            line.diff_sale = diff * line.sale_price
            line.status = ('surplus' if diff > 0.0001
                           else 'shortage' if diff < -0.0001 else 'ok')
