# -*- coding: utf-8 -*-
{
    "name": "POS Sotuvchi Tanlash",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "POS da sotuvchi tanlash",
    "depends": ["point_of_sale", "hr"],
    "data": [
        "views/pos_order_views.xml",
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_salesperson/static/src/patch_order.js",
            "pos_salesperson/static/src/SalespersonPopup.js",
            "pos_salesperson/static/src/SalespersonPopup.xml",
            "pos_salesperson/static/src/SalespersonButton.js",
            "pos_salesperson/static/src/SalespersonButton.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
