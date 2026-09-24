# -*- coding: utf-8 -*-
{
    'name': "Feliza — Каталог товаров в Складе",
    'summary': "Добавление товаров через каталог (кнопка «Каталог») в складских операциях",
    'description': """
Добавляет кнопку «Каталог» на складские операции (stock.picking) — приёмки,
отгрузки и внутренние перемещения. Позволяет добавлять товары в документ так же,
как в Коммерческих предложениях и Заказах на закупку: в виде карточек каталога
с указанием количества.

Реализовано через штатный механизм Odoo product.catalog.mixin — товары,
добавленные из каталога, создаются как строки перемещения (stock.move).
    """,
    'author': "Feliza",
    'website': "",
    'category': 'Inventory/Inventory',
    'version': '19.0.1.0.7',
    'license': 'LGPL-3',
    'depends': ['stock', 'product'],
    'data': [
        'views/stock_picking_views.xml',
        'views/stock_warehouse_views.xml',
    ],
    'post_init_hook': '_init_main_warehouse',
    'assets': {
        'web.assets_backend': [
            'feliza_stock_catalog/static/src/product_catalog/order_line.js',
            'feliza_stock_catalog/static/src/product_catalog/order_line.xml',
            'feliza_stock_catalog/static/src/product_catalog/order_line.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
