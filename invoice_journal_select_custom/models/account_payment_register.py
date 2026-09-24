import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


def _real_id(record_id):
    """account.payment.register onchange holatida ishlaganda uning
    available_journal_ids maydoni haqiqiy (int) ID'lar o'rniga
    virtual `NewId(origin=<haqiqiy_id>)` obyektlarini qaytarishi mumkin.
    `NewId` bilan oddiy int hech qachon teng bo'lmagani uchun (`==`),
    to'g'ridan-to'g'ri recordset kesishmasi (`&`) bunday holatda
    hech narsa topa olmay, natija doim bo'sh chiqib qolardi.
    Shu funksiya har doim solishtirish uchun yaroqli haqiqiy ID'ni
    qaytaradi."""
    return getattr(record_id, 'origin', None) or record_id


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.depends('payment_type', 'company_id', 'can_edit_wizard')
    def _compute_available_journal_ids(self):
        super()._compute_available_journal_ids()

        for wizard in self:
            allowed_journals = wizard.env.user.x_allowed_journal_ids
            if not allowed_journals:
                continue

            std_journals = wizard.available_journal_ids
            allowed_real_ids = set(allowed_journals.ids)

            wizard.available_journal_ids = std_journals.filtered(
                lambda j: _real_id(j.id) in allowed_real_ids
            )

            if not wizard.available_journal_ids:
                _logger.warning(
                    "Foydalanuvchi '%s' uchun ruxsat etilgan jurnallar "
                    "kompaniya/to'lov turiga mos standart jurnallar bilan "
                    "kesishmadi. Jurnal maydoni bo'sh qoladi.",
                    wizard.env.user.login,
                )
