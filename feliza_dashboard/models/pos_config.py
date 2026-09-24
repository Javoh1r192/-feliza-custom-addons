# -*- coding: utf-8 -*-
"""
DO'KON BIRLIGI
==============
Odoo'da "do'kon" degan model yo'q — pos.config (kassa) bor. Ko'p
tarmoqlarda bitta do'konda 2–3 ta kassa turadi. Agar ularni
birlashtirmasa, panelda 15 emas 25 ta "do'kon" ko'rinadi.

Shuning uchun pos.config ga ixtiyoriy "Do'kon guruhi" maydoni qo'shamiz.
Bo'sh qoldirilsa — kassaning o'z nomi do'kon nomi bo'ladi.
"""
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    feliza_store_group = fields.Char(
        string="Do'kon guruhi",
        help="Bitta do'konda bir nechta kassa bo'lsa, ularning hammasiga "
             "BIR XIL nom yozing (masalan «Chilonzor»). Panelda ular "
             "bitta do'kon bo'lib ko'rinadi.\n\n"
             "Bo'sh qoldirilsa — kassaning o'z nomi ishlatiladi.")

    feliza_store_name = fields.Char(
        string="Panel nomi", compute="_compute_feliza_store_name", store=True,
        help="Panelda ko'rinadigan do'kon nomi.")

    @api.depends("feliza_store_group", "name")
    def _compute_feliza_store_name(self):
        for rec in self:
            rec.feliza_store_name = (rec.feliza_store_group or "").strip() or rec.name

    # ------------------------------------------------------------------ #
    @api.model
    def _feliza_store_map(self, configs=None):
        """{do'kon nomi: [config id, ...]} xaritasini qaytaradi."""
        if configs is None:
            configs = self.sudo().search([
                ("company_id", "in", self.env.companies.ids),
            ])
        store_map = {}
        for cfg in configs:
            key = (cfg.feliza_store_group or "").strip() or cfg.name
            store_map.setdefault(key, []).append(cfg.id)
        return store_map
