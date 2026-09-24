import uuid

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    web_order_id = fields.Char(string="WEB Order ID", copy=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("web_order_id"):
                vals["web_order_id"] = str(uuid.uuid4())

        return super().create(vals_list)