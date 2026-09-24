# -*- coding: utf-8 -*-
import re
from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def pos_qr_search_partner(self, config_id, raw):
        """QR / skaner apparatidan kelgan telefon raqami bo'yicha mijozni topadi.

        Muhim: raqam DB tomonida NORMALLASHTIRILADI (barcha bo'sh joy, '+', '-', '(' ')'
        olib tashlanadi), shuning uchun kontakt qanday formatda saqlangan bo'lsa ham
        (masalan "+998 90 123 45 67") topiladi. 50 000+ kontakt uchun ishlaydi.

        get_new_partner bilan bir xil struktura qaytaradi — POS uni avtomatik yuklaydi.
        """
        config = self.env['pos.config'].browse(config_id)
        digits = re.sub(r'\D', '', raw or '')
        partners = self.browse()

        if digits and len(digits) >= 4:
            # Milliy raqam (oxirgi 9 raqam) bo'yicha ham qidiramiz — mamlakat kodi
            # farq qilsa ham topilsin.
            tail = digits[-9:] if len(digits) >= 9 else digits

            phone_norm = "regexp_replace(coalesce(phone,''), '[^0-9]', '', 'g')"
            conds = ["%s LIKE %%s" % phone_norm, "%s LIKE %%s" % phone_norm]
            params = ['%' + digits + '%', '%' + tail + '%']

            # Ba'zi instansiyalarda 'mobile' maydoni ham bo'lishi mumkin
            if 'mobile' in self._fields:
                mobile_norm = "regexp_replace(coalesce(mobile,''), '[^0-9]', '', 'g')"
                conds += ["%s LIKE %%s" % mobile_norm, "%s LIKE %%s" % mobile_norm]
                params += ['%' + digits + '%', '%' + tail + '%']

            where = " OR ".join(conds)
            # To'liq mos kelganini birinchi o'ringa qo'yamiz
            sql = """
                SELECT id FROM res_partner
                WHERE active = true AND (%s)
                ORDER BY (%s = %%s) DESC, id DESC
                LIMIT 20
            """ % (where, phone_norm)
            self.env.cr.execute(sql, params + [digits])
            ids = [row[0] for row in self.env.cr.fetchall()]
            partners = self.browse(ids)

        fiscal_positions = partners.fiscal_position_id
        return {
            'res.partner': self._load_pos_data_read(partners, config),
            'account.fiscal.position':
                self.env['account.fiscal.position']._load_pos_data_read(fiscal_positions, config),
        }
