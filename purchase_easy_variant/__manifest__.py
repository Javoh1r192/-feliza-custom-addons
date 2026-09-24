{
    'name': 'Purchase Easy Variant',
    'version': '19.0.1.6.0',
    'category': 'Purchase',
    'summary': 'Tez mahsulot yaratish va variant tanlash (Purchase uchun)',
    'description': """
        Purchase orderga mahsulot qo'shishni osonlashtiradi:
        - Yangi mahsulot uchun sodda shakl (faqat nom, kategoriya, atributlar, narx)
        - Barcha variantlar jadvalda - miqdor va narx kiritish
        - Mahsulot yaratishda tracking va POS avtomatik yoniq
        - Xarid qatorida RASM ustuni: tovarni suratga olib shu yerning
          o'zida qo'yish mumkin, rasm mahsulotga yoziladi
    """,
    'author': 'Custom',
    'depends': ['purchase', 'product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_variant_wizard_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
