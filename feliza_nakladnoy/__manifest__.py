# -*- coding: utf-8 -*-
{
    "name": "Feliza: nakladnoy (ombor hujjati)",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Qabul, jo'natish va ichki ko'chirish hujjatlarining yangi ko'rinishi",
    "description": """
FELIZA NAKLADNOY
================
Odoo'ning standart ombor hujjati xodim uchun noqulay edi: shtrix-kod
ustuni joy egallaydi, tovar nomi bilan rang-o'lcham bir katakda
qorishib ketadi, hujjatning o'zi haqida esa deyarli hech narsa yo'q.

Bu modul ikkala hujjatni ham qayta chizadi:
    * TEPADA — hujjat pasporti: kim yaratdi, kim qabul qildi,
      qayerdan qayerga, nechta tur, nechta dona, jami summa.
    * JADVALDA — nomi, artikuli, rangi va o'lchami ALOHIDA
      ustunlarda; talab va bajarilgan miqdor yonma-yon.
    * PASTDA — topshirdi/qabul qildi imzo joylari.

Shtrix-kod ustuni olib tashlandi — u xodimga kerak emas, birkada bor.

Summa SOTISH narxida hisoblanadi. Tannarx bu hujjatda umuman
ko'rsatilmaydi.

Qo'llanadi: Qabul (IN), Jo'natish (OUT) va ichki ko'chirishlarga.
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "report/paperformat.xml",
        "report/report_nakladnoy.xml",
        "report/report_actions.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
}
