# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    exclude_analytic_account_types = fields.Selection(
        selection=[
            ('cash_bank', 'Cash and Bank Accounts Only (Recommended)'),
            ('all_balance_sheet', 'All Balance Sheet Accounts'),
            ('none', 'Apply to All Accounts'),
        ],
        string='Exclude Analytic Distribution',
        default='cash_bank',
        config_parameter='auto_analytic_distribution.exclude_account_types',
        help="""
        Qaysi hisoblardan analitik distribyutsiyani chiqarib tashlash:
        
        - Cash and Bank (Tavsiya): Faqat kassa va bank hisoblaridan (5010.x, 5110.x)
        - All Balance Sheet: Barcha balans hisoblaridan (aktivlar, passivlar)
        - Apply to All: Hamma hisobga analitik qo'yish (ehtiyotkor!)
        """
    )
