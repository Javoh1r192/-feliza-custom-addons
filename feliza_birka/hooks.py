# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

from .models.artikul_seed import (map_categories_to_series,
                                  seed_artikul_series, sync_series_last_code)


def post_init_hook(env):
    """O'rnatishdan keyin artikul seriyalarini bazaga qarab to'ldiradi."""
    if not hasattr(env, "cr"):          # eski imzo: (cr, registry)
        env = api.Environment(env, SUPERUSER_ID, {})
    seed_artikul_series(env)
    map_categories_to_series(env)
    sync_series_last_code(env)
