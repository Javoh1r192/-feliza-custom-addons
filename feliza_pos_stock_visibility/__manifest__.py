# -*- coding: utf-8 -*-
{
    'name': "Feliza POS Stock Visibility (Ombor qoldig'i POS'da ko'rinsin)",
    'version': '19.0.1.1.0',
    'category': 'Sales/Point of Sale',
    'summary': "Ombor cheklovi (record rule) POS mahsulot ma'lumot oynasidagi "
               "qoldiqni to'smasligi uchun — POS'da barcha ombor qoldig'i ko'rinadi",
    'description': """
Feliza POS Stock Visibility
===========================
Muammo: 'stock.quant' ga qo'yilgan record rule (foydalanuvchi faqat o'z ombori
qoldig'ini ko'radi) POS mahsulot ma'lumot oynasidagi "Sklad" ro'yxatiga ham ta'sir
qiladi — natijada kassirga boshqa omborlar 0 bo'lib ko'rinadi.

Yechim: POS mahsulot ma'lumot metodi (get_product_info_pos) ombor qoldiqlarini
SUDO bilan (faqat ko'rsatish uchun) qayta hisoblaydi. Shunda:
- POS'da barcha ombor qoldig'i ko'rinadi (record rule to'smaydi),
- Backend (Inventory / astatka ro'yxati)da esa record rule o'z kuchida qoladi —
  foydalanuvchi faqat o'z ombori qoldig'ini ko'radi.

Record rule o'zgartirilmaydi — bu modul faqat POS ko'rsatishini sudo qiladi.
""",
    'author': "Feliza Sfera",
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'stock'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
