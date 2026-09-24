# -*- coding: utf-8 -*-
from odoo import fields, models


class CustomerWalletTransaction(models.Model):
    """Mijoz hamyonidagi (cashback balansidagi) har bir harakatning audit yozuvi.

    Bu model hech qachon to'g'ridan-to'g'ri (backenddan qo'lda) yaratilmasligi kerak —
    har doim ``res.partner._wallet_adjust()`` orqali yaratiladi, shunda
    ``res.partner.wallet_balance`` va shu yerdagi ``balance_after`` doim sinxron qoladi.
    """

    _name = "customer.wallet.transaction"
    _description = "Mijoz hamyoni harakati"
    _order = "create_date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner", string="Mijoz", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        "res.company", string="Kompaniya", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", string="Valyuta", related="company_id.currency_id", store=True
    )
    amount = fields.Monetary(
        string="Summa",
        required=True,
        help="Musbat son = balansga qo'shildi (cashback berildi / to'ldirildi). "
        "Manfiy son = balansdan yechildi (cashback to'lov sifatida ishlatildi).",
    )
    balance_after = fields.Monetary(
        string="Harakatdan keyingi balans", readonly=True,
        help="Ushbu harakat amalga oshirilgandan so'ng mijozning umumiy hamyon balansi.",
    )
    transaction_type = fields.Selection(
        [
            ("cashback_earned", "Cashback hisoblandi"),
            ("cashback_used", "Cashback to'lov sifatida ishlatildi"),
            ("manual_topup", "Qo'lda to'ldirildi"),
            ("manual_adjustment", "Qo'lda tuzatildi"),
        ],
        string="Turi",
        required=True,
        index=True,
    )
    pos_order_id = fields.Many2one(
        "pos.order", string="POS buyurtma", ondelete="set null", index=True
    )
    account_move_id = fields.Many2one(
        "account.move", string="Buxgalteriya provodkasi", ondelete="set null"
    )
    note = fields.Char(string="Izoh")
