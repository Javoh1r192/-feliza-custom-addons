from odoo import fields, models, api, _
from odoo.exceptions import UserError

class UserDomainAccess(models.Model):
    _name = 'user.domain.access'
    _description = 'User Domain Access Rules'

    model_id = fields.Many2one('ir.model', string="Model",ondelete='cascade', required=True)
    model_name = fields.Char(string="Model Technical Name", related='model_id.model', store=True, readonly=True)
    assignment_domain = fields.Char('Assignment Domain')
    access_rights_management_id = fields.Many2one('access.rights.management', string="Access Rights Group", ondelete="cascade")

    # user.domain.access
    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res