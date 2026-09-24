# -*- coding: utf-8 -*-
{
    "name": "Feliza POS: artikul bo'yicha chek qidirish",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "«Заказы» oynasidagi qidiruvga «Artikul» qo'shiladi",
    "description": """
POS — ARTIKUL BO'YICHA QIDIRISH
===============================
Odoo'ning «Заказы» ekranida chekni faqat 5 xil ma'lumot bo'yicha topish
mumkin edi: havola, chek raqami, hisob-faktura raqami, sana va mijoz.
Tovarning ARTIKULI bo'yicha topib bo'lmasdi — kassir «shu tovar qaysi
chekda sotilgan?» degan savolga javob topa olmasdi.

Bu modul qidiruv ro'yxatiga oltinchi bandni qo'shadi: «Artikul».
Artikulni yozsangiz, o'sha tovar qatnashgan cheklar chiqadi.

QANDAY ISHLAYDI
---------------
  * Tasdiqlangan (sinxronlangan) cheklar — serverda qidiriladi:
    lines.product_id.default_code bo'yicha. Ya'ni butun tarix bo'ylab,
    faqat ekrandagi sahifada emas.
  * Ochiq (hali yopilmagan) cheklar — brauzerning o'zida, chekdagi
    qatorlarning artikullari bo'yicha.

Boshqa hech narsaga tegilmaydi: mavjud 5 ta qidiruv turi ham o'z
o'rnida qoladi, chek, sotuv ekrani va hisobotlar o'zgarmaydi.
Modul o'chirilsa — hammasi eski holiga qaytadi.
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "feliza_pos_artikul_search/static/src/js/artikul_search.js",
        ],
    },
    "installable": True,
    "application": False,
}
