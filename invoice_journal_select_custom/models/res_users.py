# models/res_users.py
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    # Foydalanuvchiga biriktirilgan jurnallar
    x_allowed_journal_ids = fields.Many2many(
        'account.journal',
        'res_users_journal_rel',
        'user_id',
        'journal_id',
        string="Ruxsat etilgan jurnallar"
    )