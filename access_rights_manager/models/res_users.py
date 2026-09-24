from odoo import fields, models, api, SUPERUSER_ID,_
from odoo.exceptions import UserError, AccessDenied
import logging

class res_users(models.Model):
    _inherit = 'res.users'

    access_rights_management_ids = fields.Many2many('access.rights.management', 'access_management_users_rel_ah', 'user_id', 'access_rights_management_id', 'Access Pack')

    def write(self, vals):
        res = super(res_users, self).write(vals)
        for access in self.access_rights_management_ids:
            if self.env.company in access.company_ids and access.readonly:
                if self.has_group('base.group_system') or self.has_group('base.group_erp_manager'):
                    raise UserError(_('It is not possible to make the admin user read-only!'))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(res_users, self).create(vals_list)
        for record in self:
            for access in record.access_rights_management_ids:
                if self.env.company in access.company_ids and access.readonly:
                    if record.has_group('base.group_system') or record.has_group('base.group_erp_manager'):
                        raise UserError(_('It is not possible to make the admin user read-only!'))
        return res
        