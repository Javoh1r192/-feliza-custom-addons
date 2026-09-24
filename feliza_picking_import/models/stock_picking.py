# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_feliza_import_lines(self):
        """Excel fayldan qator yuklash oynasini ochadi."""
        self.ensure_one()
        if self.state in ("done", "cancel"):
            raise UserError(
                _("Hujjat yakunlangan yoki bekor qilingan — "
                  "qator qo'shib bo'lmaydi."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Excel'dan tovar yuklash"),
            "res_model": "feliza.picking.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_picking_id": self.id,
                "active_model": "stock.picking",
                "active_id": self.id,
            },
        }
