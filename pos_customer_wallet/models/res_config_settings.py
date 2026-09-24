# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_wallet_loyalty_program_id = fields.Many2one(
        related="company_id.pos_wallet_loyalty_program_id", readonly=False,
        string="Cashback Loyalty dasturi",
    )
