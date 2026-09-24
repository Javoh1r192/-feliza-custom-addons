# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class CustomerWalletAdjustmentWizard(models.TransientModel):
    """Menejer uchun: mijoz hamyon balansini qo'lda to'ldirish yoki tuzatish.

    POS savdosi orqali BO'LMAGAN har qanday balans o'zgarishi (masalan, mijozga
    qo'lda bonus berish yoki xatoni tuzatish) shu oyna orqali amalga oshiriladi —
    shunda ham audit jurnali (customer.wallet.transaction), ham
    res.partner.wallet_balance doim sinxron qoladi.
    """

    _name = "customer.wallet.adjustment.wizard"
    _description = "Mijoz hamyon balansini qo'lda tuzatish"

    partner_id = fields.Many2one(
        "res.partner", string="Mijoz", required=True,
        default=lambda self: self.env.context.get("active_id"),
    )
    current_balance = fields.Monetary(
        string="Joriy balans", related="partner_id.wallet_balance", readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    amount = fields.Monetary(
        string="Summa", required=True,
        help="Musbat son balansni oshiradi, manfiy son kamaytiradi.",
    )
    note = fields.Char(string="Sabab", required=True)

    def action_apply(self):
        self.ensure_one()
        if not self.amount:
            raise UserError(_("Summani kiriting (0 dan farqli)."))
        self.partner_id._wallet_adjust(
            self.amount, "manual_adjustment", note=self.note, allow_negative=True,
        )
        return {"type": "ir.actions.act_window_close"}
