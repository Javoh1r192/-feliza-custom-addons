from odoo import fields, models, api, _
from odoo.exceptions import UserError

class HideChatter(models.Model):
    _name = 'model.hide.chatter'
    _description = 'Model Hide Chatter'

    access_rights_management_id = fields.Many2one('access.rights.management', string="Access Rights Group", ondelete="cascade")
    model_id = fields.Many2one('ir.model', string="Model", required=True, ondelete='cascade')
    hide_chatter = fields.Boolean(default=False)

    # user.domain.access
    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res