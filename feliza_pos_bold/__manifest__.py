# -*- coding: utf-8 -*-
{
    'name': 'Feliza POS — Tovar nomlari BOLD',
    'version': '19.0.1.0.0',
    'summary': "POS'da mahsulot nomlari va atributlarini qalin (bold) ko'rsatadi",
    'description': """
POS mahsulot ekranida va buyurtma satrlarida tovar nomlari hamda
atributlarni qalin (bold) qilib ko'rsatadi. Faqat ko'rinish (CSS) —
bazaga, narxga, miqdorga tegmaydi. Qaytarish: modulni o'chirish (uninstall)
kifoya — POS avvalgi holatiga qaytadi.
""",
    'category': 'Point of Sale',
    'author': 'Claude for Feliza',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'feliza_pos_bold/static/src/css/bold.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
