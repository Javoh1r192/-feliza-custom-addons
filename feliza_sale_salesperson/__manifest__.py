# -*- coding: utf-8 -*-
{
    "name": "Feliza: Sotuv sotuvchilari (Asosiy) + KPI asosi",
    "version": "19.0.1.0.0",
    "summary": "Sotuv buyurtmalarida alohida sotuvchi (POS'dan farqli), "
               "har sotuvchi bo'yicha savdo yig'indisi (KPI uchun asos)",
    "description": """
Asosiy (optom) sotuv buyurtmalari uchun ALOHIDA sotuvchilar ro'yxati —
POS sotuvchilaridan va tizim foydalanuvchilaridan mustaqil.

  * Sotuvchilarni qo'lda kiritish/boshqarish (Sotuv > Sozlash > Sotuvchilar).
  * Har buyurtmaga bitta sotuvchi biriktiriladi (saqlanadi, tracking bilan).
  * Har sotuvchi kartochkasida: buyurtmalar soni va jami savdo summasi —
    KPI hisoblash uchun tayyor asos (aniq KPI formulasi keyin qo'shiladi).
""",
    "category": "Sales",
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_salesperson_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
