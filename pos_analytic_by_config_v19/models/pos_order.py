# Copyright 2015 ACSONE SA/NV
# Copyright 2020 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _generate_pos_order_invoice(self):
        """
        Invoice yaratishda pos_config_id ni context ga o'rnatamiz.
        Odoo 19 da pos.order.config_id compute field orqali
        session_id.config_id dan keladi — to'g'ri ishlaydi.
        """
        self = self.with_context(pos_config_id=self.config_id.id)
        return super()._generate_pos_order_invoice()
