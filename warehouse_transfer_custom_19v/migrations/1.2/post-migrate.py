# -*- coding: utf-8 -*-
"""
Bir martalik migratsiya: 1.1 -> 1.2

SABAB
-----
`_compute_interwh_report_status()` va `_resync_delivery_outstanding()`
qoldiqni shunday tekshirardi:

        if outstanding > rounding:

`rounding` — bu "Product Unit" o'nlik aniqligidan kelib chiqadigan
yaxlitlash qadami (Odoo 19: `10 ** -decimal_precision`). Feliza bazasida
"Product Unit" aniqligi 0 ga qo'yilgan, ya'ni **rounding = 1.0**.

Natijada ROSA 1 DONA qoldiq uchun shart `1.0 > 1.0` = False bo'lib,
o'sha qator hisobotga UMUMAN TUSHMAY qolardi. Kiyim savdosida bir dona
qatorlar ko'pchilikni tashkil qiladi, shuning uchun yo'qotish sezilarli.

Misol (20.08.2026 zaxirasi, Asosi/OUT/00015):
    haqiqatda jo'natilgan : 112 dona / 49 qator
    hisobotga tushgan     :  78 dona / 15 qator
    yo'qolgan             :  34 dona / 34 qator (hammasi 1 donalik)

TUZATISH
--------
Shart `float_compare(outstanding, 0.0, precision_rounding=rounding) > 0`
ga almashtirildi — ya'ni "qoldiq noldan kattami" degan to'g'ri savol.

Bu skript esa allaqachon bazada saqlangan (store=True) noto'g'ri
qiymatlarni majburan qayta hisoblaydi.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Picking = env["stock.picking"]
    Move = env["stock.move"]

    cr.execute("""
        SELECT COALESCE(SUM(interwh_report_qty), 0), COUNT(*)
          FROM stock_move
         WHERE interwh_report_status IS NOT NULL
    """)
    before = cr.fetchone()

    relevant = Picking.search([
        "|",
        ("destination_warehouse_id", "!=", False),
        ("inter_wh_delivery_id", "!=", False),
    ])
    moves = Move.search([("picking_id", "in", relevant.ids)])
    moves |= Move.search([("origin_returned_move_id", "!=", False)])

    if moves:
        moves._compute_real_warehouses()
        moves._compute_interwh_report_status()
        moves.flush_recordset()

    cr.execute("""
        SELECT COALESCE(SUM(interwh_report_qty), 0), COUNT(*)
          FROM stock_move
         WHERE interwh_report_status IS NOT NULL
    """)
    after = cr.fetchone()

    _logger.info(
        "warehouse_transfer_custom_19v 1.2: %s ta harakat qayta hisoblandi. "
        "Hisobotdagi miqdor: %s dona / %s qator -> %s dona / %s qator.",
        len(moves), before[0], before[1], after[0], after[1],
    )
