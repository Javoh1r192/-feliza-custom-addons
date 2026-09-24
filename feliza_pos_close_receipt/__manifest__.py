# -*- coding: utf-8 -*-
{
    'name': "Feliza POS: Kassa yopish cheki",
    'summary': "Kassa yopilganda kunlik chek (to'lov usullari + naxt farqi)",
    'author': "SferaIT",
    'category': 'Point of Sale',
    'version': '19.0.1.1.0',
    'depends': ['point_of_sale'],
    'data': [
        'report/close_receipt.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'feliza_pos_close_receipt/static/src/js/close_autoprint.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
