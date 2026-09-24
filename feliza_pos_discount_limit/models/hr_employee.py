# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    pos_max_discount = fields.Float(
        string="POS: Maksimal chegirma (%)",
        default=100.0,
        help="Bu xodim (kassir) POS kassada bera oladigan eng katta chegirma foizi.\n"
             "100 = cheksiz (standart). Masalan 25 qo'yilsa, 25% dan ortiq chegirma "
             "bera olmaydi. (Xodim PIN/beyji bilan kiradigan kassalar uchun.)",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        parent = super()
        if not hasattr(parent, '_load_pos_data_fields'):
            return ['id', 'name', 'pos_max_discount']
        fields_list = parent._load_pos_data_fields(config)
        if 'pos_max_discount' not in fields_list:
            fields_list = fields_list + ['pos_max_discount']
        return fields_list


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    pos_max_discount = fields.Float(readonly=True)
