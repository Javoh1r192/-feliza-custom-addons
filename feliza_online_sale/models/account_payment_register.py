# -*- coding: utf-8 -*-
from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.depends('payment_type', 'company_id', 'can_edit_wizard')
    def _compute_available_journal_ids(self):
        """Online sotuv to'lovida (feliza_online_pay context) jurnal ro'yxati
        FAQAT online jurnallar bilan cheklanadi (nomida 'online')."""
        super()._compute_available_journal_ids()
        if self.env.context.get('feliza_online_pay'):
            online = self.env['account.journal'].search([
                ('type', 'in', ('bank', 'cash')),
                ('name', 'ilike', 'online'),
            ])
            for wizard in self:
                wizard.available_journal_ids = \
                    (wizard.available_journal_ids & online) or online
