# -*- coding: utf-8 -*-
"""
Bir martalik migratsiya: 1.0 -> 1.1

Modulga "Omborlar aro tarqatish hisoboti" qo'shilishidan oldin amalga
oshirilgan barcha eski transferlarni ham yangi hisobotga qo'shadi.

Ikki qadam:

1. PUSH-OQIM TUZATISHI: Eski versiyada Delivery orqali avtomatik yaratilgan
   Receipt'lar (_create_inter_warehouse_receipt) faqat matn ko'rinishidagi
   "origin" maydoni orqali (masalan "MAIN/OUT/00021") o'z Delivery'siga
   "bog'langan" edi - haqiqiy (Many2one) inter_wh_delivery_id maydoni
   BO'SH edi. Hisobot mahz shu maydonga tayanadi, shuning uchun bu yerda
   nom bo'yicha moslashtirib, retroaktiv bog'laymiz.

   Pull/zayavka oqimidagi eski Receipt'lar bunga muhtoj emas - ular har
   doim ham inter_wh_delivery_id'ga ega bo'lgan (yaratilishidayoq
   _create_delivery_from_zayavka orqali to'g'ridan-to'g'ri yozilgan).

2. QAYTA HISOBLASH: Yuqoridagi bog'lash natijasida (va umuman eski
   ma'lumotlar uchun) stock.move'dagi hisoblanadigan maydonlarni
   (real_source_warehouse_id, real_dest_warehouse_id,
   interwh_report_status, interwh_report_qty) majburan qayta hisoblaymiz.

Modul yangilanishida Odoo yangi qo'shilgan "store=True" maydonlarni odatda
o'zi ham avtomatik qayta hisoblaydi, lekin (1)-qadamdagi bog'lash aynan
shu skript orqali amalga oshgani uchun, undan keyingi qayta hisoblashni
ham shu yerda aniq bajaramiz - ikkala holatda ham xavfsizlik uchun.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Picking = env["stock.picking"]
    Move = env["stock.move"]

    # ------------------------------------------------------------------ #
    # 1. Push-oqimdagi eski Receipt'larni Delivery'siga bog'lash          #
    # ------------------------------------------------------------------ #
    receipts_to_link = Picking.search(
        [
            ("picking_type_code", "=", "incoming"),
            ("inter_wh_delivery_id", "=", False),
            ("origin", "!=", False),
        ]
    )
    linked_count = 0
    for receipt in receipts_to_link:
        delivery = Picking.search(
            [
                ("name", "=", receipt.origin),
                ("picking_type_code", "=", "outgoing"),
                ("destination_warehouse_id", "!=", False),
            ],
            limit=1,
        )
        if delivery:
            receipt.inter_wh_delivery_id = delivery.id
            linked_count += 1

    _logger.info(
        "warehouse_transfer_custom_19v migratsiyasi: %s ta eski Receipt "
        "o'z Delivery'siga retroaktiv bog'landi.",
        linked_count,
    )

    # ------------------------------------------------------------------ #
    # 2. Tegishli barcha move'larni qayta hisoblash                       #
    # ------------------------------------------------------------------ #
    relevant_pickings = Picking.search(
        [
            "|",
            ("destination_warehouse_id", "!=", False),
            ("inter_wh_delivery_id", "!=", False),
        ]
    )
    moves = Move.search([("picking_id", "in", relevant_pickings.ids)])
    # "Return" (qaytarish) harakatlarini ham qamrab olish - ular boshqa
    # picking'larga tegishli bo'lishi mumkin.
    moves |= Move.search([("origin_returned_move_id", "!=", False)])

    if moves:
        moves._compute_real_warehouses()
        moves._compute_interwh_report_status()

    _logger.info(
        "warehouse_transfer_custom_19v migratsiyasi: %s ta harakat uchun "
        "hisobot maydonlari qayta hisoblandi.",
        len(moves),
    )
