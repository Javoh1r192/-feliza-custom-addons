# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import models


def _fz_safe(text):
    """Matnni HTML numeric-entity ga aylantiradi (Kirill/maxsus belgilar
    wkhtmltopdf da buzilmasligi uchun — birka bilan bir xil usul)."""
    if not text:
        return Markup('')
    return Markup(''.join(('&#%d;' % ord(c)) if ord(c) > 127 else c
                          for c in str(text)))


def _fz_money(amount):
    """Summani '68 066 500 so'm' ko'rinishida (nbsp ISHLATMAYDI — oddiy
    probel, aks holda wkhtmltopdf 'Â' chiqaradi)."""
    return '{:,.0f}'.format(amount or 0.0).replace(',', ' ') + ' som'


class PosSession(models.Model):
    _inherit = "pos.session"

    def _feliza_close_data(self):
        """Kassa yopish chekи uchun tayyor (ASCII-xavfsiz) ma'lumot."""
        self.ensure_one()
        self.env.cr.execute(
            "SELECT COALESCE(pm.name->>'en_US', pm.name::text) AS nomi, "
            "       COALESCE(SUM(pp.amount), 0) AS summa "
            "FROM pos_payment pp "
            "JOIN pos_payment_method pm ON pm.id = pp.payment_method_id "
            "JOIN pos_order po ON po.id = pp.pos_order_id "
            "WHERE po.session_id = %s "
            "GROUP BY pm.id, pm.name "
            "ORDER BY summa DESC",
            (self.id,))
        payments = [{'name': _fz_safe(r[0]), 'amount': _fz_money(r[1])}
                    for r in self.env.cr.fetchall()]
        total_pay = 0.0
        self.env.cr.execute(
            "SELECT COALESCE(SUM(pp.amount),0) FROM pos_payment pp "
            "JOIN pos_order po ON po.id = pp.pos_order_id "
            "WHERE po.session_id = %s", (self.id,))
        total_pay = self.env.cr.fetchone()[0] or 0.0
        self.env.cr.execute(
            "SELECT count(*), COALESCE(SUM(amount_total), 0) "
            "FROM pos_order WHERE session_id = %s AND state != 'cancel'",
            (self.id,))
        oc, otot = self.env.cr.fetchone()
        # Naxt kirim/chiqim (harajatlar): payment_ref = "<sessiya>-out-<sabab>"
        # yoki "-in-". Yopishdagi farq yozuvlari (Обнаружено расхождение) EMAS.
        self.env.cr.execute(
            "SELECT payment_ref, amount FROM account_bank_statement_line "
            "WHERE pos_session_id = %s "
            "AND (payment_ref LIKE '%%-out-%%' OR payment_ref LIKE '%%-in-%%') "
            "ORDER BY id", (self.id,))
        cash_moves = []
        cash_out_total = 0.0
        cash_in_total = 0.0
        for ref, amt in self.env.cr.fetchall():
            ref = ref or ''
            amt = amt or 0.0
            if '-out-' in ref:
                reason = ref.split('-out-', 1)[1]
            elif '-in-' in ref:
                reason = ref.split('-in-', 1)[1]
            else:
                reason = ref
            is_out = amt < 0
            if is_out:
                cash_out_total += -amt
            else:
                cash_in_total += amt
            cash_moves.append({'name': _fz_safe(reason),
                               'amount': _fz_money(amt), 'is_out': is_out})
        diff = self.cash_register_difference or 0.0
        return {
            'cash_moves': cash_moves,
            'has_cash_moves': bool(cash_moves),
            'cash_out_total': _fz_money(cash_out_total),
            'cash_in_total': _fz_money(cash_in_total),
            'config': _fz_safe(self.config_id.name),
            'cashier': _fz_safe(self.user_id.name),
            'start_at': self.start_at,
            'stop_at': self.stop_at,
            'order_count': oc or 0,
            'order_total': _fz_money(otot or 0.0),
            'payments': payments,
            'total_payments': _fz_money(total_pay),
            'cash_start': _fz_money(self.cash_register_balance_start or 0.0),
            'cash_expected': _fz_money(self.cash_register_balance_end or 0.0),
            'cash_real': _fz_money(self.cash_register_balance_end_real or 0.0),
            'cash_diff': _fz_money(diff),
            'cash_diff_neg': diff < 0,
            'sess_name': _fz_safe(self.name),
        }
