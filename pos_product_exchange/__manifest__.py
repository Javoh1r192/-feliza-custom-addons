# -*- coding: utf-8 -*-
{
    'name': "POS Product Exchange (Mahsulot Almashtirish)",
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': "Kassada (POS) sotilgan mahsulotni boshqa mahsulotga almashtirish imkoniyati",
    'description': """
POS Product Exchange
=====================
Ushbu modul Point of Sale kassa ekraniga "Almashtirish" (Exchange) tugmasini
qo'shadi. Kassir avval sotilgan buyurtmadan mahsulot(lar)ni tanlab, ularni
qaytarish bilan bir vaqtda o'sha buyurtma ichida yangi mahsulot qo'shib,
narx farqini yakuniy to'lovda hisoblashi mumkin.

Texnik yondashuv:
- Modul Odoo'ning tayyor "Refund" (qaytarish) mexanizmini o'zgartirmasdan,
  faqat uning natijasidan foydalanadi (patch orqali kengaytirish), shuning
  uchun boshqa modullarning POS'ga kiritgan o'zgarishlariga ta'sir qilmaydi.
- Yangi maydon: pos.order.is_exchange - shu buyurtma almashtirish orqali
  yaratilganini backendda (hisobotlarda, buyurtmalar ro'yxatida) ko'rsatish
  uchun ishlatiladi.
- Hech qanday mavjud model yoki view to'liq almashtirilmaydi (replace),
  faqat xpath orqali qo'shimchalar kiritiladi - shu bilan boshqa
  modullar bilan mos kelish (compatibility) ta'minlanadi.
""",
    'author': "Feliza Sfera",
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_exchange/static/src/app/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
