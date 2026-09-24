# -*- coding: utf-8 -*-
{
    "name": "Feliza — Hujjatdagi tovar hisoblagichi",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Ombor hujjatida qatorlar soni va jami dona jonli ko'rinib turadi",
    "description": """
FELIZA — HUJJAT HISOBLAGICHI
============================
Ombor hujjatlarida (qabul, jo'natma, ichki ko'chirish, inventarizatsiya)
tovarlar ro'yxati tepasida jonli hisoblagich chiqadi:

  * Qatorlar    — nechta tovar nomi kiritilgan
  * Talab       — jami so'ralgan dona
  * Kiritilgan  — jami haqiqatda kiritilgan dona
  * Farq        — ikkalasi orasidagi farq (mos kelsa «✓ To'liq» chiqadi)

NEGA KERAK: Odoo tovarlar ro'yxatini sahifalarga bo'ladi (1-40 / 49).
Jadval ostidagi yig'indi FAQAT ko'rinib turgan sahifani qo'shadi —
qolgan qatorlar hisobga kirmaydi. Bu hisoblagich esa hujjatning
BARCHA qatorlarini serverda sanaydi, sahifadan qat'i nazar.

Bekor qilingan (cancel) qatorlar hisobga olinmaydi.

TEZLIK: maydonlar bazaga YOZILMAYDI (store=False) — shuning uchun
sotuv, POS yoki ombor operatsiyalariga hech qanday qo'shimcha yuk
bermaydi. Faqat hujjat ochilganda hisoblanadi.
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "views/stock_picking_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "feliza_picking_counter/static/src/scss/counter.scss",
        ],
        "web.assets_web_dark": [
            "feliza_picking_counter/static/src/scss/counter.dark.scss",
        ],
    },
    "installable": True,
    "application": False,
}
