# -*- coding: utf-8 -*-
"""TOVAR KARTASIDAN BIRKA CHOP ETISH

Mahsulot (yoki variant) kartasidagi tugma -> variantlar + har biriga birka
soni -> chop etish. Mavjud birka shabloni (`report_feliza_label`) va barkod
mantiqi (`feliza.picking.label`) qayta ishlatiladi — ko'rinish bir xil.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FelizaProductLabelWizard(models.TransientModel):
    _name = "feliza.product.label.wizard"
    _description = "Tovar kartasidan birka chop etish"

    product_tmpl_id = fields.Many2one("product.template", "Mahsulot")
    line_ids = fields.One2many(
        "feliza.product.label.wizard.line", "wizard_id", "Variantlar")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        tmpl = self.env["product.template"]
        variants = self.env["product.product"]
        if model == "product.template" and active_id:
            tmpl = tmpl.browse(active_id)
            variants = tmpl.product_variant_ids
        elif model == "product.product" and active_id:
            p = self.env["product.product"].browse(active_id)
            tmpl = p.product_tmpl_id
            # bitta variant kartasidan kelsa — faqat o'shani ko'rsatamiz
            variants = p
        if tmpl:
            res["product_tmpl_id"] = tmpl.id
            res["line_ids"] = [(0, 0, {
                "product_id": v.id,
                "qty": 1,
                "price": v.list_price,
            }) for v in variants]
        return res

    # ---- birka shabloni chaqiradigan metodlar (stock.picking'dagidek) ----
    def _feliza_label_scale(self):
        return self.env["stock.picking"]._feliza_label_scale()

    def _feliza_label_total(self):
        return sum(int(l.qty or 0)
                   for w in self for l in w.line_ids if l.qty and l.qty > 0)

    def _feliza_label_rows(self):
        self.ensure_one()
        Label = self.env["feliza.picking.label"]
        rows = []
        for line in self.line_ids.filtered(
                lambda x: x.product_id and x.qty and x.qty > 0):
            data = Label._fz_product_label_data(
                line.product_id, price=line.price, old_price=line.old_price)
            rows.extend([data] * int(line.qty))
        off = self.env.context.get("fz_off")
        if off is not None:
            lim = self.env.context.get("fz_lim") or len(rows)
            rows = rows[off:off + lim]
        return rows

    def action_print(self):
        self.ensure_one()
        if self._feliza_label_total() <= 0:
            raise UserError(_("Kamida bitta variantga birka soni kiriting."))
        return self.env.ref(
            "feliza_birka.action_report_product_label").report_action(self)


class FelizaProductLabelWizardLine(models.TransientModel):
    _name = "feliza.product.label.wizard.line"
    _description = "Tovar birka qatori"
    _order = "id"

    wizard_id = fields.Many2one(
        "feliza.product.label.wizard", required=True, ondelete="cascade")
    # required EMAS: formada bo'sh qator paydo bo'lsa saqlashда yiqilmasin —
    # bo'sh (product_id siz) qatorlar _feliza_label_rows/_total da filtrlanadi.
    product_id = fields.Many2one("product.product", "Variant")
    barcode = fields.Char(related="product_id.barcode", readonly=True)
    qty = fields.Integer("Birka soni", default=1)
    price = fields.Float("Narx", digits="Product Price")
    old_price = fields.Float(
        "Eski narx (chegirma)", digits="Product Price",
        help="To'ldirilsa birka SARIQ chiqadi, bu narx chizilgan bo'ladi.")
