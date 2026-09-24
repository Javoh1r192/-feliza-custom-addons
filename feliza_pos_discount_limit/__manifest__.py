# -*- coding: utf-8 -*-
{
    'name': "Feliza POS Discount Limit (Chegirma cheklovi)",
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': "Har foydalanuvchi/kassir uchun POS'da maksimal chegirma foizini cheklash",
    'description': """
Feliza POS Discount Limit
=========================
Har bir foydalanuvchi (res.users) va kassir-xodim (hr.employee) uchun POS kassada
bera oladigan eng katta chegirma foizini belgilash imkonini beradi.

- Foydalanuvchi/xodim kartochkasida "POS: Maksimal chegirma (%)" maydoni.
  Standart: 100% (cheksiz). Masalan 25 qo'ysangiz, o'sha kassir 25% dan ortiq
  chegirma bera olmaydi.
- POS kassada belgilangan limitdan oshiq chegirma kiritilsa, avtomatik limitgacha
  kamaytiriladi va ogohlantirish chiqadi (numpad "%", barcode — barcha yo'llar).
- Qo'shimcha xavfsizlik: server tomonida ham tekshiriladi, shuning uchun
  frontendni chetlab o'tib ham limitdan oshiq chegirmali buyurtma saqlanmaydi.

Texnik yondashuv:
- Odoo modellari yoki templatelari REPLACE qilinmaydi — faqat maydon qo'shiladi,
  view'larga yangi sahifa qo'shiladi va POS store metodi (setDiscountFromUI)
  patch orqali kengaytiriladi. Boshqa POS modullari bilan mos keladi.
""",
    'author': "Feliza Sfera",
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'hr'],
    'data': [
        'views/res_users_views.xml',
        'views/hr_employee_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'feliza_pos_discount_limit/static/src/app/discount_limit.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
