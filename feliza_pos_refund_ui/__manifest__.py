# -*- coding: utf-8 -*-
{
    "name": "Feliza POS: qaytarish oynasini kattalashtirish",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "«Заказы» (qaytarish) ekranida tovarlar ro'yxatiga ko'proq joy",
    "description": """
POS — QAYTARISH OYNASI
======================
Odoo'ning «Заказы» ekranida qaytariladigan tovarlar ro'yxati juda kichik
bo'lib qoladi: panel kengligi qat'iy 450px (planshetda 400px), balandlikni
esa numpad, «Возврат» tugmasi va boshqaruv tugmalari egallab oladi —
ro'yxatga 2-3 qatorgina joy qoladi.

Bu modul FAQAT o'sha ekranga ta'sir qiladi:
  * panel kengaytiriladi (katta ekranda 42% gacha)
  * tovar qatorlari ro'yxatiga kafolatlangan balandlik beriladi
  * past ekranda (balandligi 900px dan kam) numpad va tugmalar
    ixchamlashtiriladi — bo'shagan joy ro'yxatga o'tadi

Sotuv ekraniga, chekka va boshqa hech narsaga tegilmaydi. Faqat CSS —
ma'lumot o'zgarmaydi, o'chirib tashlansa hammasi eski holiga qaytadi.
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "feliza_pos_refund_ui/static/src/scss/refund_ui.scss",
        ],
    },
    "installable": True,
    "application": False,
}
