# -*- coding: utf-8 -*-
{
    'name': 'Auto Analytic Distribution by Journal',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Automatically set analytic distribution based on selected journal',
    'description': """
        Kassadan chiqim/kirim kiritganda jornal asosida analitik hisobni avtomatik tanlab beradi.
        
        Masalan:
        - Naqd D3 jurnalida chiqim -> Analitik: Seul D3
        - Naqd D1 jurnalida chiqim -> Analitik: Solnichniy D1
        
        Odoo 19.0 Enterprise Edition uchun maxsus versiya.
    """,
    'author': 'Kalilbr Books',
    'depends': ['account', 'analytic'],
    'data': [
        'views/account_journal_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
