# Copyright 2020 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountAnalyticDistributionModel(models.Model):
    _inherit = "account.analytic.distribution.model"

    pos_config_id = fields.Many2one(
        comodel_name="pos.config",
        ondelete="cascade",
        help="Select a Point of Sale for which the analytic distribution will be used",
    )

    def _get_distribution(self, vals):
        """
        Odoo 19: context dagi pos_config_id ni vals ga qo'shib,
        faqat shu POS konfiguratsiyasiga mos analitik modelni topadi.
        """
        vals = vals.copy()
        pos_config_id = self.env.context.get("pos_config_id")
        if pos_config_id:
            vals["pos_config_id"] = pos_config_id
        return super()._get_distribution(vals)

    def _get_default_search_domain_vals(self):
        """
        Odoo 19: _get_applicable_models bu metoddan default qiymatlarni oladi.
        pos_config_id ni qo'shmasak, domain qurishda e'tiborga olinmaydi.
        False = universal (barcha configlar uchun).
        """
        res = super()._get_default_search_domain_vals()
        res["pos_config_id"] = False
        return res
