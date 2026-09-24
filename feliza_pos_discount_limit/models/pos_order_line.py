# -*- coding: utf-8 -*-
import logging

from odoo import models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    # ------------------------------------------------------------------ #
    #  Aksiya (loyalty) chegirmalari                                       #
    # ------------------------------------------------------------------ #
    def _feliza_aksiya_mukofotlari(self):
        """Kassada faol turgan, foizli chegirma beradigan mukofotlar.

        Bir marta o'qib olinadi — har bir qator uchun qayta so'rov
        yubormaymiz.
        """
        try:
            return self.env['loyalty.reward'].sudo().search([
                ('reward_type', '=', 'discount'),
                ('discount_mode', '=', 'percent'),
                ('program_id.active', '=', True),
                ('program_id.pos_ok', '=', True),
            ])
        except Exception:
            _logger.exception("Feliza: aksiya mukofotlarini o'qib bo'lmadi")
            return self.env['loyalty.reward'].sudo().browse()

    def _feliza_aksiya_foizlari(self, line, mukofotlar):
        """Shu TOVARGA aksiya dasturi beradigan chegirma foizlari.

        Kassir qo'lda 50% yozib qo'ya olmaydi — faqat o'sha tovarga
        haqiqatan aksiya belgilangan bo'lsagina 50% o'tadi.
        """
        foizlar = set()
        tovar = line.product_id
        for r in mukofotlar:
            try:
                if r.discount_applicability != 'specific':
                    # butun buyurtmaga yoki eng arzon tovarga beriladigan
                    # chegirma — ayrim tovarga bog'liq emas
                    foizlar.add(round(r.discount or 0.0, 2))
                    continue
                mos = False
                if r.discount_product_ids and tovar in r.discount_product_ids:
                    mos = True
                elif r.all_discount_product_ids and tovar in r.all_discount_product_ids:
                    mos = True
                else:
                    # ro'yxat o'rniga shart (domen) ishlatilgan bo'lsa
                    try:
                        if tovar.filtered_domain(r._get_discount_product_domain()):
                            mos = True
                    except Exception:
                        pass
                if mos:
                    foizlar.add(round(r.discount or 0.0, 2))
            except Exception:
                _logger.exception(
                    "Feliza: mukofot %s ni tekshirib bo'lmadi", r.id)
        return foizlar

    # ------------------------------------------------------------------ #
    @api.constrains('discount')
    def _feliza_check_discount_limit(self):
        """Server tomonidagi xavfsizlik to'sig'i.

        Kassir QO'LDA bergan chegirma uning limitidan oshmasligi kerak.
        Aksiya dasturi (Skidki i loyalnost) bergan chegirma esa cheklovga
        TUSHMAYDI — u tizimda oldindan belgilangan va kassirga bog'liq emas.
        """
        mukofotlar = None
        for line in self:
            discount = line.discount or 0.0
            if discount <= 0:
                continue
            order = line.order_id
            if not order:
                continue

            # Amaldagi kassirni aniqlash: avval xodim (pos_hr), keyin foydalanuvchi
            cashier = False
            if 'employee_id' in order._fields and order.employee_id:
                cashier = order.employee_id
            elif order.user_id:
                cashier = order.user_id
            if not cashier:
                continue

            max_disc = getattr(cashier, 'pos_max_discount', 100.0)
            if max_disc is None:
                max_disc = 100.0

            # Float xatoligiga kichik yo'l qo'yish
            if discount <= max_disc + 0.001:
                continue

            # Limitdan oshdi — bu aksiya chegirmasi bo'lishi mumkin
            if mukofotlar is None:
                mukofotlar = self._feliza_aksiya_mukofotlari()
            if round(discount, 2) in self._feliza_aksiya_foizlari(line, mukofotlar):
                continue          # tizimdagi aksiya — ruxsat

            raise ValidationError(_(
                "Chegirma cheklovi: %(name)s eng ko'pi bilan %(max)s%% chegirma "
                "bera oladi (kiritilgan: %(disc)s%%).",
                name=cashier.name or '',
                max=max_disc,
                disc=discount,
            ))
