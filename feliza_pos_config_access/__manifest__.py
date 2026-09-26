# -*- coding: utf-8 -*-
{
    'name': 'Feliza POS Kassa Access',
    'version': '19.0.1.0.0',
    'summary': "Foydalanuvchini o'z kassalari (POS) sessiya/buyurtmalari bilan cheklash",
    'description': """
Feliza POS Kassa Access
=======================
Har bir foydalanuvchiga "Ruxsat etilgan kassalar" (POS) biriktiriladi:

* Maydon BO'SH bo'lsa  -> foydalanuvchi BARCHA kassalarni ko'radi (admin/boshqaruvchi).
* Kassa(lar) tanlansa   -> faqat o'sha kassalarga aloqador POS sessiya va buyurtmalar ko'rinadi.

Faqat KO'RISH (read) filtri -- savdoga (order create/write) xalaqit bermaydi.
Kassa o'zgartirilganda ir.rule keshi avtomatik tozalanadi (darhol kuchga kiradi).
    """,
    'author': 'Feliza / SferaIT',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'data': [
        'security/pos_config_access_rules.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
