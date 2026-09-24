# -*- coding: utf-8 -*-
{
    "name": "Feliza POS: sinxron kafolati (savdolar yo'qolmasin)",
    "version": "19.0.1.0.0",
    "summary": "Barcha savdolar serverga yuborilishini kafolatlaydi — "
               "orqa fonda majburiy sinxron, tab yopilishida ogohlantirish",
    "description": """
POS savdolari mahalliy (brauzer) xotirada qolib, keyingi kun boshqa smenaga
tushib qolishining oldini oladi:

  1) Orqa fonda har 20 soniyada yuborilmagan buyurtmalar MAJBURIY sinxron
     qilinadi (internet bor bo'lsa).
  2) Internet uzilib-ulanganda darhol sinxron qilinadi.
  3) Kassir tab/oynani yopmoqchi bo'lsa va yuborilmagan savdo bo'lsa —
     brauzer ogohlantirish beradi.

Odoo'ning o'z mexanizmi (yopishda sync) saqlanadi; bu modul faqat qo'shimcha
himoya qatlamlari qo'shadi.
""",
    "category": "Point of Sale",
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "feliza_pos_sync_guard/static/src/js/sync_guard.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
