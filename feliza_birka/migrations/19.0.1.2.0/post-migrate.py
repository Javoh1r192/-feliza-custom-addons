# -*- coding: utf-8 -*-
"""Modul YANGILANGANDA ham seriyalar to'ldirilsin.

`post_init_hook` faqat birinchi o'rnatishda ishlaydi. Feliza serverida
modul allaqachon o'rnatilgan, shuning uchun yangilashda ham bir marta
to'ldirib qo'yamiz. Seriyalar allaqachon bo'lsa — tegilmaydi.
"""
from odoo import api, SUPERUSER_ID

from odoo.addons.feliza_birka.models.artikul_seed import seed_artikul_series


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    seed_artikul_series(env)
