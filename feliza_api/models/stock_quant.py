from odoo import api, models

# Shu maydonlardan biri o'zgarsa - qoldiq Feliza'ga qayta yuboriladi.
TRACKED_QUANT_FIELDS = {"quantity", "reserved_quantity"}


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _feliza_online_only(self):
        return self.filtered(lambda q: q.location_id.warehouse_id.name == "Online Ombor")

    def write(self, vals):
        result = super().write(vals)

        if TRACKED_QUANT_FIELDS & set(vals.keys()):
            products = self._feliza_online_only().mapped("product_id").filtered(
                lambda p: p.product_tmpl_id.x_publish_web
            )
            products._feliza_push_stock_updated(reason="stock_change")

        return result

    @api.model_create_multi
    def create(self, vals_list):
        quants = super().create(vals_list)

        products = quants._feliza_online_only().mapped("product_id").filtered(
            lambda p: p.product_tmpl_id.x_publish_web
        )
        products._feliza_push_stock_updated(reason="stock_change")

        return quants
