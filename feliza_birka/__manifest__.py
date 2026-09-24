# -*- coding: utf-8 -*-
{
    "name": "Feliza: artikul, barkod va birka",
    "version": "19.0.1.12.0",
    "category": "Inventory/Inventory",
    "summary": "Zakupda avto artikul/barkod, 58x40 birka chop etish, "
               "qabul qiluvchi ombor qoldig'i",
    "description": """
FELIZA — ARTIKUL, BARKOD VA BIRKA
=================================

1. AVTO ARTIKUL VA BARKOD (zakup oynasida)
   Purchase Easy oynasida YANGI mahsulot yaratilganda:
     * artikul (default_code) — MAHSULOTGA bitta, nechta variant bo'lsa ham
     * barkod — HAR BIR VARIANTGA alohida, EAN-13 (nazorat raqami bilan)
   Raqamlar Sozlamalarda ko'rsatilgan oxirgi raqamdan davom etadi.
   Navbatdagi raqam bandligi tekshiriladi — band bo'lsa, xatolik bermasdan
   keyingisiga o'tadi. Mavjud mahsulotga hech qachon yangi raqam berilmaydi.
   Artikul mahsulot KATEGORIYASIGA qarab o'z seriyasidan olinadi
   (kiyim 1xxxxx, atir 4xxxxx, sumka 6xxxxx va h.k.).
   Avto berishni Sozlamalardan alohida-alohida O'CHIRIB qo'yish mumkin —
   u holda artikul/barkodni xodim qo'lda kiritadi.

2. BIRKA CHOP ETISH (58x40 mm)
   Ombor hujjatida «Birka» bo'limi: hujjatdagi tovarlar soni bilan tayyor
   turadi, kerak bo'lsa kamaytirib/ko'paytirib chop etiladi.
   POS «Skidki i loyalnost» dagi aksiyaga tushgan tovar — SARIQ birka,
   eski narx chizilgan holda ko'rsatiladi.

3. QABUL QILUVCHI OMBOR QOLDIG'I
   Hujjat qatorlarida «Upakovka» va «Talab» orasida yangi ustun:
   tovardan qabul qiluvchi omborda (do'konda) hozir qancha borligi.
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": [
        "stock", "product", "purchase",
        "purchase_easy_variant",   # zakup oynasi shu modulda
        "loyalty",                 # POS chegirma dasturlari
        "point_of_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/report_charset.xml",
        "report/label_paperformat.xml",
        "report/label_report.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
        "views/stock_picking_views.xml",
        "report/product_label_report.xml",
        "views/product_label_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "feliza_birka/static/src/js/picking_scan.js",
            "feliza_birka/static/src/xml/picking_scan.xml",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
