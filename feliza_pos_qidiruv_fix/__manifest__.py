# -*- coding: utf-8 -*-
{
    "name": "Feliza POS — mijoz qidiruvi tuzatmasi",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "Telefon bo'yicha mijoz qidiruvi kun davomida ishlashda "
               "davom etishi uchun tuzatma.",
    "description": """
Odoo 19 POS'da mijoz qidiruvining «offsetBySearch» hisoblagichi bitta
so'rov matni uchun sessiya davomida yig'ilib boradi va hech qachon
nolga qaytmaydi. Natijada:

  1) kassir bir raqamni qidiradi — topiladi (hisoblagich 1 ga chiqadi);
  2) keyinroq XUDDI SHU raqamni yana qidirsa, server qidiruvi 1-yozuvdan
     BOSHLAB qidiradi — yagona mos yozuvni tashlab ketadi va "No more
     customer found" qaytaradi;
  3) bo'sh natijadan keyin hisoblagichga yana +100 qo'shiladi — endi bu
     so'rov POS yangilanmaguncha (F5) UMUMAN topilmaydi.

Kassalarda POS ertalabdan kechgacha yopilmasligi sababli bu har kuni
"mijoz bir topiladi, bir topilmaydi" bo'lib seziladi.

Tuzatma: kassir Enter bosganda shu so'rov uchun hisoblagich har doim
0 dan boshlanadi — server qidiruvi doim to'liq bajariladi. Takror
yozuvlar baribir qo'shilmaydi (loadedPartnerIds himoyasi bor).
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "feliza_pos_qidiruv_fix/static/src/partner_search_fix.js",
        ],
    },
    "installable": True,
}
