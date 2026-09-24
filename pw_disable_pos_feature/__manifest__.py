# -*- coding: utf-8 -*-
{
    "name" : "POS Access Right",
    "version" : "1.0",
    "category" : "Point of Sale",
    'summary': 'This apps helps you to Allow/Disable POS Features like Discount, Change Price, Payment, Quantity, Remove Orderline | Allow/Disable pos features | Restriction of POS User | POS Access Rules | Point of Sale Access Rights | Allow/Disable POS Features Point of Sales Access rights',
    'author': "Dilshodbek",
    "depends" : ['point_of_sale', 'hr'],
    "data": [
        'views/res_users_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            # 'pw_disable_pos_feature/static/src/**/*',
            'pw_disable_pos_feature/static/src/overrides/components/product_screen/sbl_product_screen.js'
            
        ],
    },
    "price": 15,
    "currency": 'EUR',
    "auto_install": False,
    "installable": True,
    "license": "LGPL-3",
    "images":['static/description/Banner.png'],
}
