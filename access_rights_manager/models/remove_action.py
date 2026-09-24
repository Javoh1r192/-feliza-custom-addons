from odoo import fields, models, api, _

class remove_action(models.Model):
    _name = 'remove.action'
    _description = "Models Right"


    access_rights_management_id = fields.Many2one('access.rights.management', 'Access rights Management')
    model_id = fields.Many2one('ir.model', 'Model')
    server_action_ids = fields.Many2many('action.data' ,'remove_action_server_action_data_rel_ah', 'remove_action_id', 'server_action_id', 'Hide Actions', domain="[('action_id.binding_model_id','=',model_id),('action_id.type','!=','ir.actions.report')]")
    report_action_ids = fields.Many2many('action.data' ,'remove_action_report_action_data_rel_ah', 'remove_action_id', 'report_action_id', 'Hide Reports', domain="[('action_id.binding_model_id','=',model_id),('action_id.type','=','ir.actions.report')]")
    readonly = fields.Boolean('Read-Only')

    restrict_create = fields.Boolean('Hide Create')
    restrict_edit = fields.Boolean('Hide Edit')
    restrict_delete = fields.Boolean('Hide Delete')
    restrict_duplicate = fields.Boolean('Hide Duplicate')
    restrict_chatter = fields.Boolean('Hide Chatter')
    restrict_import = fields.Boolean('Hide import')
    restrict_export = fields.Boolean('Hide Export')
    restrict_archive = fields.Boolean('Hide Archive/Unarchive')
