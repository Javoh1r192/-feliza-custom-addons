# -*- coding: utf-8 -*-
"""Разумное значение по умолчанию для «основного склада».

Поле `stock.warehouse.feliza_catalog_main` управляет тем, остаток какого
склада показывается вторым числом на карточке каталога. Чтобы после
установки не пришлось ничего искать вручную, галочка ставится
автоматически — но только если её ещё никто не ставил.

Выбор: склад с наибольшим остатком (это и есть основной распределительный
склад). Если остатков нет вообще — первый склад компании.
"""
import logging

_logger = logging.getLogger(__name__)


def _init_main_warehouse(env):
    Wh = env['stock.warehouse'].sudo()
    if Wh.search_count([('feliza_catalog_main', '=', True)]):
        return                     # админ уже выбрал — не трогаем

    warehouses = Wh.search([])
    if not warehouses:
        return

    env.cr.execute("""
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
    row = env.cr.fetchone()
    main = Wh.browse(row[0]) if row else warehouses[0]
    main.feliza_catalog_main = True
    _logger.info(
        "feliza_stock_catalog: основным складом для каталога выбран «%s». "
        "Изменить можно в карточке склада.", main.name,
    )
