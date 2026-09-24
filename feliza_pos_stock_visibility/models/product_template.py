# -*- coding: utf-8 -*-
from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_product_info_pos(self, price, quantity, pos_config_id, product_variant_id=False):
        """POS mahsulot ma'lumot oynasidagi ombor qoldiqlarini SUDO bilan qayta
        hisoblaymiz. Aks holda 'stock.quant' record rule tufayli kassirga boshqa
        omborlar 0 bo'lib ko'rinadi.

        MUHIM: super() qoldiqni kassir huquqi bilan hisoblab, natijani (0 larni)
        cache'ga yozadi. qty_available kontekstga bog'liq bo'lgani va cache su-flagni
        farqlamagani uchun, sudo bilan qayta o'qishdan OLDIN cache'ni tozalaymiz —
        shundagina superuser sifatida haqiqiy qoldiq qayta hisoblanadi.

        Faqat KO'RSATISH uchun — backenddagi (Inventory) record rule o'z kuchida qoladi.
        """
        res = super().get_product_info_pos(
            price, quantity, pos_config_id, product_variant_id=product_variant_id
        )

        config = self.env['pos.config'].browse(pos_config_id)
        product_variant = (
            self.env['product.product'].browse(product_variant_id)
            if product_variant_id else False
        )
        products = (product_variant or self.product_variant_ids).sudo()
        warehouses = self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', config.company_id.id)]
        )

        stock_fields = ['qty_available', 'free_qty', 'virtual_available']
        warehouse_list = []
        for w in warehouses:
            prod_w = products.with_context(warehouse_id=w.id)
            # super() ning cheklangan (0) qiymatlarini cache'dan tozalaymiz
            prod_w.invalidate_recordset(stock_fields)
            warehouse_list.append({
                'id': w.id,
                'name': w.name,
                'available_quantity': sum(prod_w.mapped('qty_available')),
                'free_qty': sum(prod_w.mapped('free_qty')),
                'forecasted_quantity': sum(prod_w.mapped('virtual_available')),
                'uom': products.uom_id.name,
            })

        # POS o'z omborini birinchi o'ringa qo'yamiz (standart tartibga mos)
        if config.picking_type_id.warehouse_id:
            warehouse_list = sorted(
                warehouse_list,
                key=lambda x: x['id'] != config.picking_type_id.warehouse_id.id,
            )

        res['warehouses'] = warehouse_list
        return res
