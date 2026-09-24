# -*- coding: utf-8 -*-
"""ESKI BO'SH VARIANTLARNI TO'LDIRISH (1.5.0 -> 1.6.0)

Bu versiyagacha mahsulotga keyinchalik qo'shilgan rang yoki o'lcham
bo'm-bo'sh qolib ketardi: artikuli ham, barkodi ham yo'q edi. Yangi
ilgak buni bundan keyin o'zi hal qiladi; bu skript esa ALLAQACHON
yaratilib qolgan bo'sh variantlarni to'ldiradi.

QOIDA
-----
    artikul — o'sha mahsulotning ENG BIRINCHI variantidan ko'chiriladi
    barkod  — yangi va betakror qilib beriladi

XAVFSIZLIK
----------
  * Faqat BO'SH kataklar to'ldiriladi — mavjud artikul yoki barkodga
    umuman tegilmaydi.
  * Mahsulotning birorta variantida ham artikul bo'lmasa, u chetlab
    o'tiladi: bunday tovarga raqamni odam o'zi berishi kerak, chunki
    qaysi seriyadan olish kerakligini skript bilmaydi.
  * Artikul xom SQL bilan yoziladi — ORM orqali yozilsa shablonning
    hisoblanadigan maydoni qayta ishga tushib, ko'p variantli
    mahsulotda artikulni o'chirib yuborardi (1.5.0 dagi sabab).
"""
import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.feliza_birka.models.feliza_numbering import (
    PARAM_AUTO_BARCODE, auto_on)

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # --- 1) qaysi variantlar bo'sh va qaysi artikul tegishli ----------
    cr.execute("""
        WITH birinchi AS (
            SELECT DISTINCT ON (product_tmpl_id)
                   product_tmpl_id, default_code
              FROM product_product
             WHERE coalesce(default_code, '') <> ''
             ORDER BY product_tmpl_id, id
        )
        SELECT p.id, b.default_code
          FROM product_product p
          JOIN birinchi b ON b.product_tmpl_id = p.product_tmpl_id
         WHERE coalesce(p.default_code, '') = ''
    """)
    qatorlar = cr.fetchall()
    if not qatorlar:
        _logger.info("Feliza: artikulsiz variant topilmadi — tuzatish shart emas")
    else:
        # bir xil artikulga tegishlilarini guruhlab yozamiz
        guruh = {}
        for pid, kod in qatorlar:
            guruh.setdefault(kod, []).append(pid)
        for kod, ids in guruh.items():
            cr.execute(
                "UPDATE product_product SET default_code = %s WHERE id IN %s",
                (kod, tuple(ids)))
        _logger.info("Feliza: %s ta variantga akasining artikuli ko'chirildi",
                     len(qatorlar))

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["product.product"].invalidate_model(["default_code"])
    env["product.template"].invalidate_model(["default_code"])

    # --- 2) o'sha variantlarga barkod ----------------------------------
    if not qatorlar or not auto_on(env, PARAM_AUTO_BARCODE):
        return
    ids = [pid for pid, _kod in qatorlar]
    variantlar = env["product.product"].with_context(
        active_test=False).browse(ids).filtered(lambda p: not p.barcode)
    if not variantlar:
        _logger.info("Feliza: barkodsiz variant qolmadi")
        return
    try:
        kodlar = env["feliza.numbering"].next_barcodes(len(variantlar))
    except Exception:                                       # noqa: BLE001
        _logger.exception(
            "Feliza: barkod navbatidan raqam olib bo'lmadi — %s ta variant "
            "barkodsiz qoldi: %s", len(variantlar), variantlar.ids)
        return
    for variant, bc in zip(variantlar, kodlar):
        variant.barcode = bc
    _logger.info("Feliza: %s ta variantga barkod berildi (%s ... %s)",
                 len(kodlar), kodlar[0], kodlar[-1])
