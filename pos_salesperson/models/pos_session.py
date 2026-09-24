# -*- coding: utf-8 -*-
from odoo import models

class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_hr_employee(self):
        return {
            "search_params": {
                "domain": [("active", "=", True)],
                "fields": ["id", "name", "job_title"],
            }
        }

    def _get_pos_ui_hr_employee(self, params):
        return self.env["hr.employee"].search_read(**params["search_params"])
