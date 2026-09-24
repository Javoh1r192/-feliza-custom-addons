# -*- coding: utf-8 -*-
from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def get_store_stock(self):
        """Shu POS ombori bo'yicha har tovar (template) umumiy qoldig'i: {tmpl_id: qty}.
        POS ochilganda jonli olinadi — mahsulot keshiga bog'liq emas."""
        self.ensure_one()
        wh = self.warehouse_id
        if wh:
            dom = [("location_id", "child_of", wh.view_location_id.id)]
        else:
            dom = [("location_id.usage", "=", "internal")]
        res = {}
        for prod, qty in self.env["stock.quant"].sudo()._read_group(
                dom, groupby=["product_id"], aggregates=["quantity:sum"]):
            tid = prod.product_tmpl_id.id
            res[tid] = res.get(tid, 0.0) + (qty or 0.0)
        return {str(k): v for k, v in res.items()}
