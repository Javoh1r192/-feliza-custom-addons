# -*- coding: utf-8 -*-
# Eski keshlangan POS klientlar bu maydonlarni so'rashi mumkin — ustunlar
# mavjud bo'lishi uchun saqlaymiz (bo'sh). Yangi badge RPC-xaritadan ishlaydi.
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"
    pos_store_total = fields.Float(default=0.0)


class ProductProduct(models.Model):
    _inherit = "product.product"
    pos_store_qty = fields.Float(default=0.0)
    pos_store_total = fields.Float(default=0.0)
