from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.http import request


class access_management(models.Model):
    _name = 'access.rights.management'
    _description = "Access rights Management"

    name = fields.Char('Name')
    user_ids = fields.Many2many('res.users', 'access_management_users_rel_ah', 'access_rights_management_id', 'user_id',
                                'Users')

    readonly = fields.Boolean('Read-Only')
    active = fields.Boolean('Active', default=True)

    hide_menu_ids = fields.Many2many('menu.item', 'access_management_menu_rel_ah', 'access_rights_management_id', 'menu_id',
                                     'Hide Menu')
    hide_field_ids = fields.One2many('hide.field', 'access_rights_management_id', 'Hide Field', copy=True)

    remove_action_ids = fields.One2many('remove.action', 'access_rights_management_id', 'Remove Action', copy=True)

    hide_view_nodes_ids = fields.One2many('hide.view.nodes', 'access_rights_management_id', 'Button/Tab Access', copy=True)

    self_module_menu_ids = fields.Many2many('ir.ui.menu', 'access_management_ir_ui_self_module_menu',
                                            'access_rights_management_id', 'menu_id', 'Self Module Menu',
                                            default=lambda self: self.env.ref('access_rights_manager.main_menu_access_rights_manager'))

    domain_access_ids = fields.One2many('user.domain.access', 'access_rights_management_id', string='Domain Access')

    hide_chatter = fields.Boolean('Hide Chatter')
    disable_import = fields.Boolean('Disable Import', default=False)
    disable_delete = fields.Boolean('Disable Delete', default=False)
    disable_developer_mode = fields.Boolean('Disable Developer Mode', default=False)
    disable_export = fields.Boolean('Disable Export', default=False)
    disable_archive = fields.Boolean('Disable Archive/Unarchive', default=False)


    disable_debug_mode = fields.Boolean('Disable Developer Mode')

    company_ids = fields.Many2many('res.company', 'access_management_comapnay_rel', 'access_rights_management_id',
                                   'company_id', 'Companies', required=True, default=lambda self: self.env.company)
    hide_chatter_ids = fields.One2many('model.hide.chatter', 'access_rights_management_id', string='Hide Chatter Models')



    def toggle_active_value(self):
        for record in self:
            record.write({'active': not record.active})
        return True

    @api.constrains('create_date')
    def _oncreate_rec(self):
        for record in self:
            record.refresh_users()
    @api.model_create_multi
    def create(self, vals_list):
        res = super(access_management, self).create(vals_list)
        request.registry.clear_cache()
        for record in res:
            if record.readonly:
                for user in record.user_ids:
                    if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
                        raise UserError(_('Admin user can not be set as a read-only..!'))
        return res

    def unlink(self):
        for record in self:
            record.refresh_users()
        res = super(access_management, self).unlink()
        request.env.registry.clear_cache()
        return res

    def write(self, vals):
        res = super(access_management, self).write(vals)

        if self.readonly:
            for user in self.user_ids:
                if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
                    raise UserError(_('Admin user can not be set as a read-only..!'))
        request.env.registry.clear_cache()
        for record in self:
            record.refresh_users()
        return res

    def refresh_users(self):
        user_ids = self.user_ids
        print("USER", user_ids)
        for user in user_ids:
            params = {"type": "custom-refresh", "payload": {"user_id": user.id}}
            self.env["bus.bus"]._sendone("custom-refresh", "notification", params)