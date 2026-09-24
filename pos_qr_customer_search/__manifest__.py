# -*- coding: utf-8 -*-
{
    'name': 'POS QR Customer Search',
    'version': '19.0.2.0.0',
    'summary': 'QR kod (kamera yoki apparat skaner) orqali POS da mijozni avtomatik topish',
    'description': """
        Point of Sale da mijozning QR kodini o'qib, avtomatik topish va tanlash.

        v2 yangiliklari:
        - Kamera BILAN BIRGA apparat (barcode/QR) skaner ham qo'llab-quvvatlanadi.
          Skaner klaviatura kabi ishlaydi (keyboard-wedge) — mijoz ekranida QR/kodni
          skanerlash kifoya, avtomatik topiladi. Kamera esa "Kamera QR" tugmasi bilan.
        - 50 000+ kontakt ichidan ishonchli qidiruv: telefon raqami DB tomonida
          normallashtiriladi (bo'sh joy, +, -, ( ) e'tiborga olinmaydi), shuning uchun
          kontakt qanday formatda saqlangan bo'lsa ham topiladi.

        QR/kod formati: telefon raqami (masalan +998901234567).
    """,
    'category': 'Point of Sale',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_qr_customer_search/static/lib/jsQR.js',
            'pos_qr_customer_search/static/src/css/qr_customer_search.css',
            'pos_qr_customer_search/static/src/xml/qr_customer_search.xml',
            'pos_qr_customer_search/static/src/js/qr_customer_search.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
