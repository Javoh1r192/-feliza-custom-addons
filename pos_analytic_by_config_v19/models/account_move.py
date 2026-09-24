from odoo import models
from .pos_session import _is_liquidity


class AccountMove(models.Model):
    _inherit = "account.move"

    def _apply_pos_analytic(self):
        """
        Agar bu move POS sessiyasiga tegishli bo'lsa,
        kassa/bank EMAS hisoblarga analitik qo'yadi.

        Qoidalar:
        - Kredit/likvid (5010, 5110, 5120) qatorlarga HECH QACHON analitik qo'yilmaydi
        - Debit (xarajat/daromad) qatorlarga faqat shu movega tegishli
          to'g'ri POS config analitigi qo'yiladi
        """
        pos_config_id = self.env.context.get("pos_config_id")

        for move in self:
            config_id = pos_config_id

            if not config_id:
                config_id = self._find_pos_config_from_move(move)

            if not config_id:
                continue

            analytic_model = self.env["account.analytic.distribution.model"]
            analytic_dist = analytic_model.with_context(
                pos_config_id=config_id
            )._get_distribution({"pos_config_id": config_id})

            if not analytic_dist:
                continue

            for line in move.line_ids:
                # Likvid (kassa/bank) hisoblar — HECH QACHON analitik qo'yilmaydi
                if _is_liquidity(line.account_id):
                    continue
                if not line.analytic_distribution:
                    line.sudo().analytic_distribution = analytic_dist

    def _find_pos_config_from_move(self, move):
        """
        move.journal_id → payment method → sessiya → config zanjiri orqali
        aynan shu movega tegishli POS config ni topadi.
        """
        # 1-usul: move.journal_id dan to'g'ridan-to'g'ri topish (eng aniq)
        if move.journal_id:
            session = self.env["pos.session"].search([
                ("payment_method_ids.journal_id", "=", move.journal_id.id),
                ("state", "in", ["opened", "closing_control", "closed"]),
            ], order="id desc", limit=1)
            if session:
                return session.config_id.id

        # 2-usul: likvid hisoblar orqali topish (fallback)
        liquidity_lines = move.line_ids.filtered(
            lambda l: _is_liquidity(l.account_id)
        )
        if not liquidity_lines:
            return False

        liquidity_accounts = liquidity_lines.mapped("account_id")

        payment_methods = self.env["pos.payment.method"].search([
            "|",
            ("journal_id.default_account_id", "in", liquidity_accounts.ids),
            ("journal_id.suspense_account_id", "in", liquidity_accounts.ids),
        ])

        if not payment_methods:
            return False

        session = self.env["pos.session"].search([
            ("payment_method_ids", "in", payment_methods.ids),
            ("state", "in", ["opened", "closing_control", "closed"]),
        ], order="id desc", limit=1)

        return session.config_id.id if session else False

    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._apply_pos_analytic()
        return moves

    def write(self, vals):
        res = super().write(vals)
        return res
