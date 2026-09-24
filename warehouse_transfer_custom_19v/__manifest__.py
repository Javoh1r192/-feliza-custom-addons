# -*- coding: utf-8 -*-
{
    "name": "Inter Warehouse Transfer Custom 19v",
    "version": "1.6",
    "category": "Inventory/Internal",
    "summary": "Omborlar aro mahsulot o'tkazishni boshqarish",
    "description": """
        Ushbu modul orqali bir ombordan ikkinchisiga mahsulot o'tkazish
        tranzit lokatsiya orqali amalga oshiriladi.

        Har bir ombor uchun ruxsat etilgan foydalanuvchilar belgilanishi mumkin.
        Faqat ruxsat etilgan foydalanuvchilar omborni ko'ra oladi va
        unda ichki o'tkazma yarata oladi.

        1.3: hujjatni QABUL QILUVCHI ombor xodimi ham ko'ra oladi.
        Ilgari qoida faqat jo'natuvchi omborni tekshirar edi, shuning
        uchun do'kon boshlig'i o'ziga kelayotgan yuk hujjatini ocholmasdi.

        1.5: KAMOMAT. Do'kon yukni kam qabul qilib «rezerv buyurtma
        kerak emas» desa, tranzitda osilib qolgan qoldiq uchun skladga
        qaytarish hujjati AVTOMAT yaratiladi. Ombor kartochkasida soni
        ko'rinadi, «Kamomat» menyusida esa qaysi Delivery bo'yicha,
        qaysi do'konda, qaysi tovardan qancha kam chiqqani ko'rinadi.
    """,
    "author": "Bobur",
    "depends": ["stock", "stock_account"],
    "data": [
        "security/ir.model.access.csv",
        "security/stock_picking_security.xml",
        "data/stock_data.xml",
        "views/warehouse_views.xml",
        "views/stock_picking_views.xml",
        "views/interwh_report_views.xml",
        "views/kamomat_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
