# -*- coding: utf-8 -*-
"""1.0.4 -> 1.0.5: выбрать основной склад для карточек каталога.

`post_init_hook` срабатывает только при УСТАНОВКЕ модуля. У Feliza модуль
уже установлен, поэтому при обновлении галочку ставит эта миграция —
иначе вторая строка («остаток на основном складе») не появилась бы,
пока админ вручную не отметит склад.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Wh = env['stock.warehouse'].sudo()
    if Wh.search_count([('feliza_catalog_main', '=', True)]):
        return

    warehouses = Wh.search([])
    if not warehouses:
        return

    cr.execute("""
        SELECT w.id, COALESCE(SUM(q.quantity), 0) AS qty
          FROM stock_warehouse w
          JOIN stock_location wl ON wl.id = w.view_location_id
          LEFT JOIN stock_location l
                 ON l.parent_path LIKE wl.parent_path || '%%'
                AND l.usage = 'internal'
          LEFT JOIN stock_quant q ON q.location_id = l.id
         WHERE w.id = ANY(%s)
         GROUP BY w.id
         ORDER BY qty DESC
         LIMIT 1
    """, (warehouses.ids,))
    row = cr.fetchone()
    main = Wh.browse(row[0]) if row else warehouses[0]
    main.feliza_catalog_main = True
    _logger.info(
        "feliza_stock_catalog 1.0.5: основной склад для каталога — «%s».",
        main.name,
    )
