# -*- coding: utf-8 -*-
"""KATEGORIYALARNI SERIYAGA BIRIKTIRISH (1.3.0 -> 1.4.0)

MUAMMO
------
Feliza kategoriyalari yassi ro'yxat: «Верхняя одежда / Куртка» degan
kategoriyaning OTASI yo'q, slash faqat nom ichida. Shu sababli
«ota kategoriyaga qarab topish» ishlamadi va o'rnatishda faqat bir
nechta kategoriya seriyaga biriktirilgan edi.

Natijada «Dvoyka», «Верхняя одежда / Куртка» kabi kategoriyalarda yangi
mahsulot yaratilganda seriya topilmay, umumiy zaxira navbatga tushib
ketardi — u yerda esa xato kiritilgan «3» turgani uchun artikul «4»
bo'lib chiqardi.

Bu skript qolgan kategoriyalarni nomiga qarab kerakli seriyaga qo'shadi
va har bir seriyaning «oxirgi artikul» qiymatini bazadagi haqiqiy eng
katta raqamga ko'taradi. Ikkalasi ham faqat QO'SHADI/KO'TARADI —
qo'lda qilingan sozlamalar buzilmaydi.
"""
import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.feliza_birka.models.artikul_seed import (
    map_categories_to_series, seed_artikul_series, sync_series_last_code)

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    seed_artikul_series(env)        # seriyalar umuman yo'q bo'lsa
    map_categories_to_series(env)   # biriktirilmagan kategoriyalar
    sync_series_last_code(env)      # raqamni haqiqiy maksimumga tenglash

    # Umumiy zaxira navbatda «3» kabi yaroqsiz qiymat qolgan bo'lsa —
    # olib tashlaymiz. Undan «4» degan artikul chiqib ketardi.
    ICP = env["ir.config_parameter"].sudo()
    raw = (ICP.get_param("feliza.birka.last_artikul") or "").strip()
    digits = "".join(c for c in raw if c.isdigit())
    if raw and (len(digits) < 6 or not raw.isdigit()):
        _logger.warning(
            "Feliza: umumiy artikul navbatidagi yaroqsiz qiymat «%s» "
            "olib tashlandi — artikul endi kategoriya seriyasidan olinadi",
            raw)
        ICP.set_param("feliza.birka.last_artikul", "")
