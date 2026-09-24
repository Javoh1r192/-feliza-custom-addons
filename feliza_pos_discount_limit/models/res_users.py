# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_max_discount = fields.Float(
        string="POS: Maksimal chegirma (%)",
        default=100.0,
        help="Bu foydalanuvchi POS kassada bera oladigan eng katta chegirma foizi.\n"
             "100 = cheksiz (standart). Masalan 25 qo'yilsa, kassada 25% dan ortiq "
             "chegirma bera olmaydi.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        """POS frontendiga joriy foydalanuvchining chegirma limitini ham yuklaymiz."""
        fields_list = super()._load_pos_data_fields(config)
        if 'pos_max_discount' not in fields_list:
            fields_list = fields_list + ['pos_max_discount']
        return fields_list
