# -*- coding: utf-8 -*-
"""1.6 — ANIQLANGAN KAMOMAT MIQDORI

`feliza_kamomat_qty` — do'kon qabulni tasdiqlagan paytda HAQIQATDA
qancha yetishmagani. `product_uom_qty` dan farqi: skladchi keyinchalik
qisman qabul qilsa, `product_uom_qty` kamayib ketadi va hisobotda
kamomat kichrayib ko'rinardi. Bu maydon esa o'zgarmaydi.

1.5 da yaratilgan hujjatlar uchun qiymat orqaga to'ldiriladi.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'stock_move'
           AND column_name = 'feliza_kamomat_qty'
    """)
    if not cr.fetchone():
        return
    cr.execute("""
        UPDATE stock_move
           SET feliza_kamomat_qty = GREATEST(
                   COALESCE(product_uom_qty, 0), COALESCE(quantity, 0))
         WHERE feliza_kamomat = TRUE
           AND (feliza_kamomat_qty IS NULL OR feliza_kamomat_qty = 0)
    """)
    _logger.info("Feliza kamomat: %s qatorga aniq miqdor yozildi", cr.rowcount)
