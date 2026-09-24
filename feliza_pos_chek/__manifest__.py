# -*- coding: utf-8 -*-
{
    "name": "Feliza POS: chekda artikul va rang-o'lcham",
    "version": "19.0.2.4.0",
    "category": "Sales/Point of Sale",
    "summary": "Chek qatorida artikul, rang va o'lcham ko'rsatiladi",
    "description": """
CHEKDA TOVAR ANIQ KO'RINSIN
===========================
Odoo chekda faqat tovar nomini yozadi. Nomida variant bo'lsa u
qavs ichida chiqadi, bo'lmasa — hech narsa. Artikul esa umuman yo'q.
Natijada mijoz ham, kassir ham chekdan qaysi tovar sotilganini aniq
ayta olmaydi: qaytarishda, almashtirishda va hisob-kitobda muammo.

Bu modul har bir chek qatoriga ostiga bitta kichik satr qo'shadi:

    Нимча рубашка 9095 (кора)
    108045 · кора, S

Ya'ni ARTIKUL va — agar nomda ko'rinmagan bo'lsa — RANG va O'LCHAM.
Boshqa hech narsaga tegilmaydi: narx, jami, QR kod va sotuv ekrani
o'z holicha qoladi.
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "feliza_pos_chek/static/src/js/chek_qatori.js",
            "feliza_pos_chek/static/src/xml/chek_qatori.xml",
            "feliza_pos_chek/static/src/scss/chek.scss",
        ],
    },
    "installable": True,
    "application": False,
}
