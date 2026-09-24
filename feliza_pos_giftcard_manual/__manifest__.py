# -*- coding: utf-8 -*-
{
    "name": "Feliza - POS Gift Card qisman ishlatish",
    "version": "19.0.1.1.0",
    "category": "Sales/Point of Sale",
    "summary": "POS'da gift card (vaucher) qatorining summasini kassir qo'lda "
               "kamaytira oladi; balansdan oshirib bo'lmaydi.",
    "description": """
Feliza - POS Gift Card qisman ishlatish
=======================================
Standart Odoo gift card'ni skanerlaganda avtomatik ravishda
min(karta balansi, order summasi) ni yechadi va bu qatorni tahrirlab bo'lmaydi.

Ushbu modul:

* Gift card reward qatorini tanlab, numpad'da "Price" rejimida summa kiritishga
  ruxsat beradi (yoki "price control" yoqilgan bo'lsa - popup orqali).
* Kiritilgan summa karta balansidan yoki order summasidan oshsa - qabul qilmaydi.
* Kiritilgan summa order o'zgarganda (mahsulot qo'shilsa/olib tashlansa) ham
  saqlanib qoladi (Odoo reward qatorlarini qayta hisoblaganda hurmat qilinadi).
* Server tomonda (confirm_coupon_programs) karta qatori qulflanadi va yechilayotgan
  summa lines.points_cost bilan mos kelishi hamda balansdan oshmasligi tekshiriladi.

Qo'shimcha:

* loyalty.card kodlari faqat raqamlardan ("044" + 10 raqam) generatsiya qilinadi -
  skaner klaviatura layout'idan qat'i nazar to'g'ri o'qiydi.
* "Coupon Code" va "Gift Card" print reportlarida chiziqli barcode o'rniga QR.
* Yangi "Vaucher QR" reporti: faqat summa + QR + kod (dizayner uchun).

Foydalanish: mahsulotlarni o'tkazing -> vaucher barcode'ini skanerlang ->
"Gift Card" qatorini tanlang -> numpad'da "Price" -> summani kiriting.
    """,
    "author": "Sfera IT Solutions",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "pos_loyalty", "loyalty"],
    "data": [
        "report/loyalty_card_reports.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "feliza_pos_giftcard_manual/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
