# -*- coding: utf-8 -*-
"""Modul o'chirilganda standart hujjatlarni qaytarish.

Biz `stock` modulining ikkita chop etish amalini o'z shablonimizga
yo'naltiramiz. Modul o'chirilsa, o'sha amallar mavjud bo'lmagan
shablonga ishora qilib qolardi va «Печать» tugmasi xato berardi.
Bu ilgak ularni asl holiga qaytaradi.
"""
import logging

_logger = logging.getLogger(__name__)

ASLIGA = {
    "stock.action_report_picking": ("stock.report_picking", "Picking Operations"),
    "stock.action_report_delivery": ("stock.report_deliveryslip", "Delivery Slip"),
}


def uninstall_hook(env):
    for xmlid, (report_name, nomi) in ASLIGA.items():
        action = env.ref(xmlid, raise_if_not_found=False)
        if not action:
            continue
        action.write({
            "report_name": report_name,
            "report_file": report_name,
            "name": nomi,
            "paperformat_id": False,
        })
        _logger.info("Feliza nakladnoy: %s asl holiga qaytarildi", xmlid)
