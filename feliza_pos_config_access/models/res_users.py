# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_pos_config_ids = fields.Many2many(
        comodel_name='pos.config',
        relation='res_users_allowed_pos_config_rel',
        column1='user_id',
        column2='pos_config_id',
        string='Ruxsat etilgan kassalar',
        help="Bo'sh qoldirilsa -- foydalanuvchi BARCHA kassalarni ko'radi. "
             "Kassa(lar) tanlansa -- faqat o'shalarga aloqador POS sessiya "
             "va buyurtmalar ko'rinadi.",
    )

    def _feliza_clear_rule_cache(self):
        # ir.rule domeni user.allowed_pos_config_ids ga bog'liq: o'zgarsa
        # kesh tozalanmasa eski holat qoladi. Shuning uchun darhol tozalaymiz.
        self.env.registry.clear_cache()

    def write(self, vals):
        res = super().write(vals)
        if 'allowed_pos_config_ids' in vals:
            self._feliza_clear_rule_cache()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if any('allowed_pos_config_ids' in (v or {}) for v in vals_list):
            self._feliza_clear_rule_cache()
        return users
