# -*- coding: utf-8 -*-
{
    'name': "POS: savat satrida artikul",
    'version': '19.0.1.0.0',
    'summary': "POS savatidagi mahsulot nomidan keyin artikulni ko'rsatadi",
    'description': """
        Kassa ekranidagi buyurtma satrlarida mahsulot nomidan keyin
        uning artikuli (default_code) badge ko'rinishida chiqadi —
        o'ng tomondagi mahsulotlar ro'yxatidagi kabi.
        Bosma chekka ta'sir qilmaydi.
    """,
    'category': 'Point of Sale',
    'author': 'Feliza',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'feliza_pos_artikul/static/src/css/orderline_artikul.css',
            'feliza_pos_artikul/static/src/js/orderline_artikul.js',
            'feliza_pos_artikul/static/src/xml/orderline_artikul.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
