# -*- coding: utf-8 -*-
{
    'name': "Feliza POS Layout (Kassa panelini sudrab kattalashtirish)",
    'version': '19.0.1.1.0',
    'category': 'Sales/Point of Sale',
    'summary': "POS kassa panelini sichqoncha/barmoq bilan sudrab o'lchash, "
               "kenglikni eslab qolish va mahsulotlar setkasini ixchamlashtirish",
    'description': """
Feliza POS Layout
=================
Point of Sale (kassa) ekranida chap panelni — buyurtma ro'yxati, raqamlar
paneli (numpad) va "To'lov" tugmasi joylashgan qismni — moslashuvchan qiladi.

Imkoniyatlar:
- Panelning o'ng chekkasidagi dastakni SUDRAB kenglikni jonli o'zgartirish.
  Sichqoncha ham, SENSOR EKRAN (barmoq) ham ishlaydi — all-in-one kassa uchun.
- Tanlangan kenglik shu qurilma brauzerida ESLAB QOLINADI (localStorage) va
  POS qayta ochilganda tiklanadi.
- Dastakni IKKI MARTA bosish -> standart kenglikka qaytaradi.
- Tortayotganda joriy kenglik (px) ko'rsatib turiladi.
- O'ng tarafdagi mahsulotlar setkasi ixchamlashtirilgan — bir ekranda ko'proq
  mahsulot ko'rinadi.
- Mobil ko'rinishda (ekran < 993px) o'chirilgan, telefon interfeysi buzilmaydi.

Texnik yondashuv:
- Faqat CSS va kichik JS qo'shiladi. Hech qanday Odoo modeli, template yoki
  Python logikasi o'zgartirilmaydi (replace yo'q) — shuning uchun
  pos_product_exchange, feliza_size_split va boshqa modullar bilan to'liq
  mos keladi.
- JS Odoo OWL komponentlariga tegmaydi; faqat brauzerdagi CSS o'zgaruvchisini
  (--feliza-leftpane-width) boshqaradi, shu sabab qayta chizishlarda (re-render)
  buzilmaydi.
""",
    'author': "Feliza Sfera",
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'feliza_pos_layout/static/src/scss/pos_layout.scss',
            'feliza_pos_layout/static/src/js/pos_resize.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
