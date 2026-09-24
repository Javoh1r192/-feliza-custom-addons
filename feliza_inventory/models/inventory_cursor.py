# -*- coding: utf-8 -*-
from odoo import fields, models


class FelizaInventoryCursor(models.Model):
    """Har FOYDALANUVCHINING sessiyadagi JORIY joyi (kursori).

    Nima uchun: bir sessiyada bir necha kishi bir vaqtda, TURLI javonlarda
    sanashi mumkin. Agar joriy joy sessiyada umumiy bo'lsa, biri joy
    skanerласа ikkinchisining tovarlari ham o'sha joyga tushib ketadi. Shuning
    uchun joriy joy har (sessiya, foydalanuvchi) uchun ALOHIDA saqlanadi.
    """
    _name = 'feliza.inventory.cursor'
    _description = "Inventarizatsiya — foydalanuvchi joriy joyi"

    _uniq_session_user = models.Constraint(
        'unique(session_id, user_id)',
        "Bir sessiyada bir foydalanuvchi uchun bitta kursor.",
    )

    session_id = fields.Many2one('feliza.inventory.session', required=True,
                                 ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', required=True, index=True,
                              default=lambda s: s.env.user)
    location_id = fields.Many2one('stock.location', "Joriy joy")
