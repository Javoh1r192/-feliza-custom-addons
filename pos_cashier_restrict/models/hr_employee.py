from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    pw_disable_discount = fields.Boolean(
        string="Chegirma (%) ni o'chirish",
        default=False,
        help="POS da bu kassirga chegirma tugmasini o'chiradi",
    )
    pw_disable_price = fields.Boolean(
        string="Narxni o'zgartirishni o'chirish",
        default=False,
        help="POS da bu kassirga narx o'zgartirish tugmasini o'chiradi",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        for f in ['pw_disable_discount', 'pw_disable_price']:
            if f not in fields_list:
                fields_list.append(f)
        return fields_list


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    pw_disable_discount = fields.Boolean(readonly=True)
    pw_disable_price = fields.Boolean(readonly=True)
