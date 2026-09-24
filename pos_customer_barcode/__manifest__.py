{
    'name': 'POS Customer Phone Barcode Search',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'POS da mijozni telefon raqami (QR kod) orqali qidirish',
    'depends': ['point_of_sale', 'barcodes'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_customer_barcode/static/src/CustomerBarcodeHandler.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
