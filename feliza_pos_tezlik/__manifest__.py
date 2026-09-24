{
    "name": "Feliza — POS ochilish tezligi",
    "version": "19.0.1.0.0",
    "summary": "Kassa ochilishidagi N+1 so'rovni guruhlab bajaradi",
    "description": """
Odoo'ning `product.template._add_archived_combinations` metodi kassa ochilganda
yuklanadigan HAR BIR mahsulot shabloni uchun alohida SQL so'rov yuboradi
(Feliza'da ~4 600 ta so'rov, ~10 soniya).

Bu modul o'sha metodni guruhlab ishlaydigan variant bilan almashtiradi:
istisnolar va arxivlangan variantlar bir necha so'rovda olinadi.

Natija bir xil — jonli ma'lumotda 4 814 ta shablonda tekshirilgan,
farq topilmadi. Vaqt: 10,31 s -> 1,64 s, so'rovlar: 4 589 -> 45.
""",
    "author": "Feliza",
    "category": "Point of Sale",
    "depends": ["point_of_sale"],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
