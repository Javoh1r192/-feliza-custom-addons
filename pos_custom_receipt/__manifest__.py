{
    'name': 'Custom PoS Receipt Discount',
    'version': '19.0.1.0.0',
    'author': 'Shahzod (Odoo 19 port)',
    'category': 'Sales/Point of Sale',
    'summary': "Chegirmani alohida «Discount» qatori o'rniga tovar qatoriga "
               "yozadi, chekda «Chegirma» yakuniy qatorini ko'rsatadi",
    'description': """
Odoo 19 uchun moslashtirilgan.

1. Foizli (percent) loyalty/discount mukofoti qo'llanganda alohida «Discount»
   qatori yaratilmaydi — chegirma foizi to'g'ridan-to'g'ri tovar qatorlariga
   yoziladi.
2. Bir xil tovar + bir xil chegirmali qatorlar bitta qatorga birlashtiriladi.
3. Tovar qatorida chegirma summasi (so'mda) qizil belgi bilan ko'rsatiladi.
4. Chekda: «Discount»/«Скидка» mukofot qatori ko'rsatilmaydi, uning o'rniga
   yakuniy summadan oldin «Chegirma» qatori chiqadi.
""",
    'depends': ['point_of_sale', 'pos_loyalty'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_custom_receipt/static/src/js/pos_store_patch.js',
            'pos_custom_receipt/static/src/js/order_line.js',
            'pos_custom_receipt/static/src/js/order_receipt.js',
            'pos_custom_receipt/static/src/xml/order_line.xml',
            'pos_custom_receipt/static/src/xml/receipt_template.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
