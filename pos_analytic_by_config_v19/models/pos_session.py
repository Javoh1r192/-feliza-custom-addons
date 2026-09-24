# Copyright 2021 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models

LIQUIDITY_PREFIXES = ('5010', '5110', '5120')


def _is_liquidity(account):
    if not account:
        return True
    if account.code and account.code.startswith(LIQUIDITY_PREFIXES):
        return True
    # account_type orqali ham tekshirish
    liquidity_types = {'asset_cash', 'asset_bank_and_cash', 'liability_credit_card'}
    if account.account_type in liquidity_types:
        return True
    return False


def _apply_analytic_to_move(move, analytic_dist):
    """
    Move ichidagi kassa/bank EMAS hisoblarga analitik yozadi.
    Likvid (kredit/kassa) hisoblarga HECH QACHON yozmaydi.
    """
    if not move or not analytic_dist:
        return
    for line in move.line_ids:
        # Likvid hisoblar (5010, 5110, 5120 va h.k.) — o'tkazib yuboriladi
        if _is_liquidity(line.account_id):
            continue
        # Faqat bo'sh analitik qatorlarga yozamiz
        if not line.analytic_distribution:
            line.sudo().analytic_distribution = analytic_dist


class PosSession(models.Model):
    _inherit = "pos.session"

    def _validate_session(self, balancing_account=False, amount_to_balance=0,
                           bank_payment_method_diffs=None):
        return super(
            PosSession, self.with_context(pos_config_id=self.config_id.id)
        )._validate_session(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs,
        )

    def try_cash_in_out(self, _type, amount, reason, partner_id, extras):
        """POS da Cash In/Out bosilganda chaqiriladi"""
        self_with_ctx = self.with_context(pos_config_id=self.config_id.id)
        result = super(PosSession, self_with_ctx).try_cash_in_out(
            _type, amount, reason, partner_id, extras
        )
        # try_cash_in_out bajarilgandan KEYIN analitik qo'yamiz
        self._apply_analytic_after_cash_in_out()
        return result

    def _get_analytic_dist(self):
        """Bu sessiyaning POS Config ga mos analitik distribyutsiyasini qaytaradi"""
        analytic_model = self.env["account.analytic.distribution.model"]
        return analytic_model.with_context(
            pos_config_id=self.config_id.id
        )._get_distribution({"pos_config_id": self.config_id.id})

    def _apply_analytic_after_cash_in_out(self):
        """
        Cash In/Out dan keyin yaratilgan eng so'nggi
        statement line ni topib, uning move iga analitik qo'yadi.

        Faqat non-likvid qatorlarga yoziladi (kredit/likvid qatorlar o'tkazib yuboriladi).
        """
        self.ensure_one()
        analytic_dist = self._get_analytic_dist()
        if not analytic_dist:
            return

        # Shu sessiya payment method journallariga tegishli oxirgi statement line
        last_line = self.env["account.bank.statement.line"].search(
            [(
                "journal_id",
                "in",
                self.payment_method_ids.mapped("journal_id").ids,
            )],
            order="id desc",
            limit=1,
        )
        if not last_line:
            return

        _apply_analytic_to_move(last_line.move_id, analytic_dist)
