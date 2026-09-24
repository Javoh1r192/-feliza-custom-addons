# -*- coding: utf-8 -*-
{
    "name": "Feliza: hujjatga Excel'dan tovar yuklash",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Ombor hujjati qatorlarini Excel (Billz eksporti) fayldan to'ldirish",
    "description": """
HUJJATGA EXCEL'DAN TOVAR YUKLASH
================================
Ombor hujjatining (qabul, yetkazish, o'tkazma) qatorlarini qo'lda emas,
Excel fayldan to'ldiradi. Fayl Billz eksporti bo'lishi mumkin — ustun
nomlari avtomat tanib olinadi.

  * mos qidirish: BARKOD bo'yicha (eng ishonchli kalit)
  * soni: «Отправлено» / «Количество» / «Qty» ustunidan
  * bir barkod bir necha marta uchrasa — qo'shib yuboriladi
  * topilmagan barkodlar ro'yxati ko'rsatiladi va CSV qilib beriladi

Hujjat tasdiqlangan (done) yoki bekor qilingan bo'lsa — o'zgartirmaydi.
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/picking_import_wizard_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
