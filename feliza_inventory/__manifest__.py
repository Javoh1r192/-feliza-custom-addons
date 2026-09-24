# -*- coding: utf-8 -*-
{
    'name': "Feliza Inventarizatsiya (skaner)",
    'summary': "Do'kon/ombor bo'yicha skaner orqali inventarizatsiya + hisobot",
    'description': """
Mustaqil inventarizatsiya moduli (Odoo yadrosiga tegmaydi):
- Do'kon/ombor tanlab sessiya ochish
- Lokatsiya barkodini -> tovar barkodlarini skanerlab sanash (+1, bitta savat)
- Kutilgan / sanalgan / sotilgan(davomida) / farq (ortiqcha·kam) + summa (tannarx·sotuv)
- Mahsulot kesimida ANIQ solishtirish (javonlar birlashadi)
- Boshlangan/tugagan vaqt va davomiylik
- Ruxsat guruhlari (kim ko'radi/qiladi)
""",
    'author': "SferaIT",
    'category': 'Inventory',
    'version': '19.0.1.11.3',
    'depends': ['stock', 'product'],
    'data': [
        'security/inventory_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/inventory_views.xml',
        'views/inventory_product_views.xml',
        'report/location_qr.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'feliza_inventory/static/src/css/inventory_scan.css',
            'feliza_inventory/static/src/js/inventory_scan.js',
            'feliza_inventory/static/src/xml/inventory_scan.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
