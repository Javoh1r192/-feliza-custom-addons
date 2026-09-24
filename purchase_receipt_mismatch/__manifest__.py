{
    'name': 'Purchase Receipt Mismatch',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Qabul miqdori farqini aniqlash va xabar berish',
    'description': """
        Omborda tovar qabul qilinganida buyurtma va qabul miqdorini solishtiradi.
        - Ro'yxatda farqli buyurtmalar rang bilan ajralib turadi
        - Tanlangan foydalanuvchiga avtomatik xabar boradi
        - PO chatteriga batafsil farq yoziladi
    """,
    'author': 'Custom',
    'depends': ['purchase', 'stock', 'mail'],
    'data': [
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
