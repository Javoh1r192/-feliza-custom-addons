from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mismatch_notify_user_id = fields.Many2one(
        'res.users',
        string='Miqdor farqi xabari uchun foydalanuvchi',
        help='Omborda qabul miqdori buyurtmadan farq qilsa, shu foydalanuvchiga xabar boradi.',
        config_parameter='purchase_receipt_mismatch.notify_user_id',
    )
