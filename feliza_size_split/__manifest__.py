# -*- coding: utf-8 -*-
{
    "name": "Feliza — Qabulda o'lchamga taqsimlash",
    "version": "19.0.1.1.0",
    "category": "Inventory/Inventory",
    "summary": "Rang bo'yicha kelgan tovarni qabul (Поступление) bosqichida "
               "o'lchamlarga (razmerlarga) bo'lib taqsimlash",
    "description": """
Qabulda o'lchamga taqsimlash
============================

Xarid (Purchase) jarayonida tovar faqat RANG bo'yicha buyurtma qilinadi
(masalan: qora — 50 ta, qizil — 50 ta). Tovar omborga kelganda esa uni
O'LCHAMLAR bo'yicha taqsimlash kerak bo'ladi (S=10, M=20, L=15, XL=5 ...).

Ushbu modul qabul (kiruvchi transfer) ekraniga "O'lchamlarga taqsimlash"
tugmasini qo'shadi. Tugma bir oynada har bir rang qatorini ko'rsatadi va
o'lchamlar bo'yicha miqdor kiritishga imkon beradi. Tasdiqlanganda qabul
qatorlari avtomatik ravishda rang+o'lcham variantlariga bo'linadi.
""",
    "author": "Feliza",
    "website": "https://feliza.sfera-erp.uz",
    "license": "LGPL-3",
    "depends": ["stock", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_attribute_views.xml",
        "views/stock_picking_views.xml",
        "wizard/size_distribution_wizard_views.xml",
    ],
    "application": False,
    "installable": True,
}
