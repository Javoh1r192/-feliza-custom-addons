# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    is_size = fields.Boolean(
        string="O'lcham atributi",
        help="Belgilansa, ushbu atribut o'lcham (razmer) o'lchovi sifatida "
             "ishlatiladi. Qabulda taqsimlash aynan shu atribut qiymatlariga "
             "qarab amalga oshiriladi. Odatda faqat bitta atribut (O'lcham) "
             "shunday belgilanadi.",
    )


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    is_size_placeholder = fields.Boolean(
        string="Belgilanmagan o'lcham",
        help="Xarid (Purchase) bosqichida ishlatiladigan vaqtinchalik "
             "'belgilanmagan' o'lcham qiymati. Tovar qabul qilinganda ushbu "
             "qiymat haqiqiy o'lchamlarga taqsimlanadi va uning o'zida hech "
             "qachon qoldiq qolmasligi kerak.",
    )
