# -*- coding: utf-8 -*-
{
    "name": "Ombor Hisoboti 19v",
    "version": "1.0",
    "category": "Inventory/Reporting",
    "summary": "Har bir ombor bo'yicha oylik kirim/chiqim/qoldiq hisoboti",
    "description": """
        OMBOR HISOBOTI
        ==============
        Har bir ombor (filial) va mahsulot bo'yicha, oylik kesimda:
          - Kirim: tasdiqlangan Purchase Order orqali kelgan miqdor
                   + omborlar aro transferdan qabul qilingan miqdor
                   + "Return" orqali qaytib kelgan miqdor
          - Chiqim: mijozga sotuv (Sales va POS) orqali chiqqan miqdor
                   + omborlar aro transferga yuborilgan miqdor
          - Qoldiq: oy oxiridagi yig'ma (running) balans
          - Qoldiq qiymati: qoldiq miqdori x mahsulotning hozirgi tannarxi

        Pivot, Ro'yxat va Grafik ko'rinishlarida.
    """,
    "author": "Bobur",
    "depends": ["stock", "stock_account", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/warehouse_report_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
