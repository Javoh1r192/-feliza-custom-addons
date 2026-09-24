# -*- coding: utf-8 -*-
{
    "name": "Mijoz hamyoni (Cashback Wallet) - POS",
    "version": "19.0.3.1.0",
    "category": "Sales/Point of Sale",
    "summary": "POS'da cashback ballarini (Odoo Loyalty) alohida to'lov usuli "
               "sifatida, qisman va overdraft nazorati bilan sarflash.",
    "description": """
Mijoz hamyoni (Wallet) va Cashback tizimi
==========================================
Cashback BALLARINI TO'PLASH (earn) qoidasi (foiz va h.k.) to'liq Odoo'ning
o'z Loyalty dasturi orqali ishlaydi. Bu modul SARFLASH (spend) tomonini
qulaylashtiradi VA to'plashda bitta tuzatish kiritadi — buyurtmaning
Cashback bilan to'langan qismi yangi ball hisob-kitobiga kirmaydi (faqat
mijoz boshqa to'lov turi orqali haqiqatda to'lagan summaga ball beriladi):

* Cashback POS'da alohida TO'LOV USULI sifatida chiqadi (mahsulot qatori
  yoki "Rewards" tugmasi orqali emas)
* Kassir mijoz balansidan xohlagan miqdorni qisman ishlatishi mumkin
* Mijoz balansidan ortiq summa yechib bo'lmaydi (overdraft nazorati,
  frontend + server darajasida)
* To'lov ekranida mijozning joriy cashback balansi (Loyalty balansidan
  hisoblab, so'mda) ko'rinib turadi
* Sarflangan summa mijozning native Odoo Loyalty kartasidan yechiladi va
  standart 'loyalty.history' audit yozuvi qoldiriladi
* Yangi ball to'plash Cashback bilan to'langan summani hisobga olmaydi —
  "ball ustidan ball" spiral effektining oldi olinadi

Batafsil o'rnatish va sozlash uchun modul ichidagi README.md ga qarang.
    """,
    "author": "Custom development",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "pos_loyalty", "loyalty"],
    "data": [
        "views/pos_payment_method_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_customer_wallet/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
