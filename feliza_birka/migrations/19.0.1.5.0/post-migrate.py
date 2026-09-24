# -*- coding: utf-8 -*-
"""ARTIKULNI VARIANTLARGA TUSHIRISH (1.4.0 -> 1.5.0)

MUAMMO
------
Modul artikulni faqat SHABLONGA yozardi. Odoo'da esa
`product.template.default_code` — hisoblanadigan maydon: u variantdan
olinadi va mahsulotda bir nechta variant bo'lsa bo'shatib qo'yiladi.
Natijada «Варианты товаров» ro'yxatida «Ички ҳавола» ustuni bo'sh
qolardi va artikul birka, POS hamda hisobotlarda ko'rinmasdi.

Feliza bazasidagi eski tovarlarda artikul aynan VARIANTNING o'zida
turibdi (bitta mahsulotning 9 ta variantida ham «106547»). Bu skript
shu tartibni tiklaydi: shabloni artikulli, lekin o'zi artikulsiz
bo'lgan variantlarga shablon artikulini ko'chiradi.

XAVFSIZLIK
----------
* Faqat BO'SH variantlar to'ldiriladi — mavjud artikulga tegilmaydi.
* Xom SQL ishlatiladi: ORM orqali yozilsa shablonning hisobi qayta
  ishga tushib, ko'p variantli shablonlarda artikulni o'chirib
  yuborardi.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE product_product p
           SET default_code = t.default_code
          FROM product_template t
         WHERE p.product_tmpl_id = t.id
           AND coalesce(t.default_code, '') <> ''
           AND coalesce(p.default_code, '') = ''
    """)
    _logger.info("Feliza: %s ta variantga shablon artikuli ko'chirildi",
                 cr.rowcount)

    # keshdagi eski qiymatlar qolib ketmasin
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["product.product"].invalidate_model(["default_code"])
    env["product.template"].invalidate_model(["default_code"])
