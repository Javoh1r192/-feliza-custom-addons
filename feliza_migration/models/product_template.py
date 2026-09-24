# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Faqat "Kim zakup qilgan" yangi (mavsum/davlat allaqachon x_studio_ da bor)
    x_zakup_qilgan = fields.Char("Kim zakup qilgan", readonly=True, copy=False,
                                 help="Migratsiyada eski tizimdan (Поставщик). "
                                      "O'zgarmas.")
