# models/product_product.py
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # SQL unique cheklovini o'chirish
    _sql_constraints = [
        ('barcode_uniq', 'CHECK(1=1)', 'Barcode does not need to be unique.')
    ]

    barcode = fields.Char(
        'Barcode',
        copy=False,
        index='btree',
        unique=False
    )

    # Odoo 19 da Aynan mana shu metod o'sha siz ko'rgan xatoni beryapti!
    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """
        Odoo sors-kodidagi asosiy validatsiyani override qilib,
        ichini bo'sh qoldiramiz. Endi xato bera olmaydi.
        """
        pass


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Shablon darajasida ham o'sha nomli metodni o'chiramiz
    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        pass