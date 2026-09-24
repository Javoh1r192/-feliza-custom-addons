# -*- coding: utf-8 -*-
"""QABUL/HUJJATDA INLINE SKANER (+1)

Skladchi hujjat formasining O'ZIDA barkod skanerlaydi:
  * tovar qatorda yo'q bo'lsa — qator ochiladi (Talab=1, Kiritilgan=1);
  * bor bo'lsa — har skanda +1 (Talab va Kiritilgan ikkisi ham).

feliza_inventory dagi skaner g'oyasi, lekin stock.picking ga (Поступления,
ichki o'tkazma va h.k.). Odoo 19: stock.move da `name` maydoni YO'Q.
"""
from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Widget uchun soxta (saqlanmaydigan) maydon.
    feliza_scan_input = fields.Char(
        string="Skaner", store=False,
        help="Barkod skanerlang — tovar qatorga +1 qo'shiladi.")

    def feliza_scan_barcode(self, code):
        """Bitta barkod skanini qayta ishlaydi. Widget (JS) chaqiradi."""
        self.ensure_one()
        code = (code or "").strip()
        if not code:
            return {"ok": False}
        if self.state in ("done", "cancel"):
            return {"ok": False,
                    "message": _("Hujjat yopilgan — skanerlab bo'lmaydi.")}
        Product = self.env["product.product"].sudo()
        product = Product.search(
            ["|", ("barcode", "=", code), ("default_code", "=", code)], limit=1)
        if not product:
            return {"ok": False, "message": _("Topilmadi: %s") % code}

        move = self.move_ids.filtered(
            lambda m: m.product_id == product and m.state != "cancel")[:1]
        if move:
            move.product_uom_qty = (move.product_uom_qty or 0.0) + 1.0
            move.quantity = (move.quantity or 0.0) + 1.0
        else:
            move = self.env["stock.move"].sudo().create({
                "picking_id": self.id,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": self.location_id.id,
                "location_dest_id": self.location_dest_id.id,
                "company_id": self.company_id.id,
            })
            move.quantity = 1.0

        done = sum(self.move_ids.filtered(
            lambda m: m.product_id == product).mapped("quantity"))
        return {"ok": True, "name": product.display_name,
                "qty": done or 1.0}
