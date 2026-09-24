# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    # Har bir jurnal uchun default analitik hisob
    default_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Default Analytic Account',
        help='Bu jurnalda yaratilgan barcha operatsiyalar uchun avtomatik analitik hisob'
    )
    
    # Yoki analitik distribyutsiya (Odoo 16+ uchun)
    default_analytic_distribution = fields.Json(
        string='Default Analytic Distribution',
        help='Bu jurnalda yaratilgan barcha operatsiyalar uchun avtomatik analitik distribyutsiya'
    )
