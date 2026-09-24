# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    """
    POS sessiyasida Cash In/Out (Pul kirim/chiqim) operatsiyalari
    yaratilganda analitik distribyutsiyani avtomatik qo'llash.

    Odoo POS-da Cash In/Out jarayoni:
      pos.session._create_cash_statement_lines_and_cash_move_lines()
      yoki
      pos.session._create_account_move() orqali account.move yaratiladi.

    Biz shu jarayondan keyin yaratilgan move.line larni ushlab,
    sessiyaning journal.default_analytic_distribution ni qo'llaymiz.
    """
    _inherit = 'pos.session'

    # ------------------------------------------------------------------ #
    #  Yordamchi: sessiyaning analitik distribyutsiyasini olish           #
    # ------------------------------------------------------------------ #
    def _get_pos_analytic_distribution(self):
        """
        Joriy POS sessiyasiga tegishli analitik distribyutsiyani qaytaradi.
        Manba: session.config_id.journal_id.default_analytic_distribution
        """
        self.ensure_one()
        journal = self.config_id.journal_id  # POS kassa jurnali
        if journal and journal.default_analytic_distribution:
            return journal.default_analytic_distribution
        return None

    # ------------------------------------------------------------------ #
    #  Asosiy override: Cash In/Out move larini yaratgandan keyin         #
    #  analitikani qo'llash                                               #
    # ------------------------------------------------------------------ #
    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        """
        Standart POS yopilish jarayonida naqd pul harakati move.line larini
        yaratuvchi metod. Biz uni override qilib, keyin analitik qo'llaymiz.
        Faqat Cash In/Out move_line larga tegamiz, savdo/refund larni
        o'zgartirmaymiz.
        """
        result = super()._create_cash_statement_lines_and_cash_move_lines(data)
        self._apply_analytic_to_cash_in_out_lines()
        return result

    def _apply_analytic_to_cash_in_out_lines(self):
        """
        Sessiya bilan bog'liq Cash In/Out account.move.line larini topib,
        ularga sessiyaning analitik distribyutsiyasini yozadi.

        Faqatgina:
          - pos_statement_id yoki ref da 'Cash In'/'Cash Out' belgisi bo'lgan
            yoki pos.session.statement orqali bog'langan move.line lar
          - analytic_distribution hali bo'sh bo'lgan qatorlar
        ga ta'sir qiladi.
        """
        for session in self:
            analytic_dist = session._get_pos_analytic_distribution()
            if not analytic_dist:
                _logger.debug(
                    'POS session %s uchun analitik distribyutsiya topilmadi, '
                    'jurnal: %s', session.name, session.config_id.journal_id.name
                )
                continue

            # POS sessiyasiga tegishli barcha account.move larni topamiz
            # (faqat Cash In/Out uchun yaratilganlar — move_type='entry',
            #  journal = POS kassa jurnali)
            cash_journal = session.config_id.journal_id
            domain = [
                ('pos_session_id', '=', session.id),
                ('journal_id', '=', cash_journal.id),
                ('move_type', '=', 'entry'),
            ]
            cash_moves = self.env['account.move'].search(domain)

            if not cash_moves:
                _logger.debug(
                    'Session %s uchun Cash move topilmadi.', session.name
                )
                continue

            lines_to_update = cash_moves.line_ids.filtered(
                lambda l: not l.analytic_distribution
                and (l.debit != 0.0 or l.credit != 0.0)
            )

            if lines_to_update:
                lines_to_update.write(
                    {'analytic_distribution': analytic_dist}
                )
                _logger.info(
                    'POS session "%s": %d ta move.line ga analitik '
                    'distribyutsiya qo\'llandi (%s).',
                    session.name,
                    len(lines_to_update),
                    analytic_dist,
                )
