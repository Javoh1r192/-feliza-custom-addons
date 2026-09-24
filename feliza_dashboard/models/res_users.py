# -*- coding: utf-8 -*-
"""
FOYDALANUVCHI ↔ DO'KON BOG'LANISHI
==================================
Do'kon boshlig'i faqat o'ziga biriktirilgan do'kon(lar)ni ko'rishi kerak.
Bu bog'lanish shu yerda saqlanadi.

XAVFSIZLIK: bu maydonni faqat "Dashboard: Rahbar" guruhidagi
foydalanuvchi tahrirlashi mumkin (views/res_users_views.xml da groups
orqali cheklangan). Aks holda do'kon boshlig'i o'ziga boshqa do'konlarni
qo'shib olishi mumkin bo'lardi.
"""
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    feliza_dashboard_config_ids = fields.Many2many(
        "pos.config",
        "feliza_dashboard_user_config_rel",
        "user_id", "config_id",
        string="Dashboard: biriktirilgan kassalar",
        help="«Dashboard: Do'kon boshlig'i» guruhidagi foydalanuvchi "
             "faqat shu kassalar ma'lumotini ko'radi.\n\n"
             "Bo'sh qoldirilsa — hech qanday ma'lumot ko'rinmaydi "
             "(xavfsizlik uchun ataylab shunday).")

    feliza_dashboard_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "feliza_dashboard_user_wh_rel",
        "user_id", "warehouse_id",
        string="Dashboard: biriktirilgan omborlar",
        help="«Dashboard: Ombor xodimi» guruhidagi foydalanuvchi "
             "faqat shu omborlar qoldig'ini va o'tkazmalarini ko'radi.\n\n"
             "Bo'sh qoldirilsa — barcha omborlarni ko'radi.")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "feliza_dashboard_config_ids", "feliza_dashboard_warehouse_ids"]
