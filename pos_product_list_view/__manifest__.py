# -*- coding: utf-8 -*-
{
    'name': 'POS Product Card / List View Toggle',
    'version': '19.0.1.0.0',
    'summary': 'POS da mahsulotlarni Card va List ko\'rinishida ko\'rsatish',
    'description': """
        Point of Sale mahsulotlar ekranida card (grid) va
        list ko'rinishi o'rtasida almashish tugmasini qo'shadi.
        Tanlangan ko'rinish brauzer xotirasida saqlanadi.
    """,
    'category': 'Point of Sale',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_list_view/static/src/css/product_list_view.css',
            'pos_product_list_view/static/src/xml/product_list_view.xml',
            'pos_product_list_view/static/src/js/product_list_view.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
