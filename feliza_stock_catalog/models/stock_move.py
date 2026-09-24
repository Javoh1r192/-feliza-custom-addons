# -*- coding: utf-8 -*-
from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.readonly
    def action_add_from_catalog(self):
        """Прокси-метод для кнопки «Каталог» внутри списка строк перемещения.

        Кнопка находится в <control> списка move_ids, поэтому проверяется на
        модели stock.move. Метод получает id документа из контекста и вызывает
        каталог на самом документе (stock.picking) — так же, как sale.order.line.
        """
        picking = self.env['stock.picking'].browse(self.env.context.get('order_id'))
        return picking.action_add_from_catalog()

    def _get_product_catalog_lines_data(self, **kwargs):
        """Информация о строках перемещения для карточки каталога.

        - пустой recordset -> только значение по умолчанию (quantity = 0);
        - одна строка       -> количество, цена и признак «только чтение»;
        - несколько строк   -> суммарное количество и режим «только чтение».
        """
        if len(self) == 1:
            catalog_info = self.picking_id._get_product_price_and_data(self.product_id)
            catalog_info.update(
                quantity=self.product_uom_qty,
                readOnly=self.picking_id._is_readonly(),
            )
            if self.product_id.uom_id != self.product_uom:
                catalog_info['uomDisplayName'] = self.product_uom.display_name
            return catalog_info
        elif self:
            self.product_id.ensure_one()
            move = self[0]
            catalog_info = move.picking_id._get_product_price_and_data(move.product_id)
            catalog_info['quantity'] = sum(self.mapped(
                lambda m: m.product_uom._compute_quantity(
                    qty=m.product_uom_qty,
                    to_unit=m.product_id.uom_id,
                )
            ))
            catalog_info['readOnly'] = True
            return catalog_info
        return {'quantity': 0}
