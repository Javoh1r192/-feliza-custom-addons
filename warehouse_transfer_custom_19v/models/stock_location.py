# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockLocation(models.Model):
    _inherit = 'stock.location'

    # Bu yerda tranzit lokatsiyani tasodifan o'chirib yubormaslik
    # yoki turini o'zgartirmaslik uchun himoya qo'shishimiz mumkin

    def unlink(self):
        """ 'Inter Warehouse Transfer' lokatsiyasini o'chirishni taqiqlash """
        for location in self:
            if location.name == 'Inter Warehouse Transfer':
                raise UserError(_(
                    "Siz 'Inter Warehouse Transfer' lokatsiyasini o'chira olmaysiz, "
                    "chunki u omborlar aro o'tkazmalar tizimi uchun zarur."
                ))
        return super(StockLocation, self).unlink()

    @api.model
    def _create_transit_location_if_not_exists(self):
        """
        Agar lokatsiya qandaydir sabab bilan o'chib ketgan bo'lsa yoki
        modul o'rnatilganda yaratilmagan bo'lsa, uni kod orqali yaratish funksiyasi.
        """
        existing_loc = self.search([
            ('name', '=', 'Inter Warehouse Transfer'),
            ('usage', '=', 'internal')
        ], limit=1)

        if not existing_loc:
            self.create({
                'name': 'Inter Warehouse Transfer',
                'usage': 'internal',
                'location_id': False, # Parent location bo'sh (Root)
                'barcode': 'INTER-WH-TRANS',
                'comment': 'Avtomatik yaratilgan tranzit lokatsiyasi.'
            })