# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def confirm_coupon_programs(self, coupon_data):
        """Gift card ballari yechilishidan oldin server tomonda tekshiruv.

        Standart oqim:
          1. validate_coupon_programs  - order yaratilishidan OLDIN balansni tekshiradi
          2. sync_from_ui              - order yaratiladi
          3. confirm_coupon_programs   - kartadan ball yechiladi (client yuborgan qiymat)

        3-qadamda client yuborgan `points` ga to'g'ridan-to'g'ri ishoniladi.
        Bu yerda: (a) karta qatori qulflanadi (ikki filial bir vaqtda ishlatsa),
        (b) yechilayotgan summa order qatorlaridagi points_cost bilan tengligi,
        (c) balansdan oshmasligi tekshiriladi.
        """
        self._feliza_check_gift_card_spending(coupon_data)
        return super().confirm_coupon_programs(coupon_data)

    def _feliza_check_gift_card_spending(self, coupon_data):
        self.ensure_one()
        data = {int(k): v for k, v in coupon_data.items()}
        existing_ids = [k for k in data if k > 0]
        if not existing_ids:
            return
        cards = self.env['loyalty.card'].sudo().browse(existing_ids).exists()
        gift_cards = cards.filtered(lambda c: c.program_id.program_type == 'gift_card')
        if not gift_cards:
            return

        # Qatorlarni qulflash: parallel ikkita order bitta kartani ishlatsa,
        # ikkinchisi birinchisi yozib bo'lguncha kutadi va haqiqiy balansni ko'radi.
        self.env.cr.execute(
            "SELECT id, points FROM loyalty_card WHERE id IN %s FOR UPDATE",
            (tuple(gift_cards.ids),),
        )
        locked_points = dict(self.env.cr.fetchall())
        gift_cards.invalidate_recordset(['points'])

        for card in gift_cards:
            delta = data[card.id].get('points', 0) or 0
            if delta >= 0:
                continue  # sotilgan/to'ldirilgan karta - bu yerda tekshirilmaydi
            spent = -delta
            line_cost = sum(
                self.lines.filtered(
                    lambda l: l.is_reward_line and l.coupon_id.id == card.id
                ).mapped('points_cost')
            )
            if float_compare(spent, line_cost, precision_digits=2) != 0:
                raise UserError(_(
                    "Vaucher %(code)s: yechilayotgan summa (%(spent)s) order "
                    "qatorlari bilan mos kelmaydi (%(cost)s). Order qayta tekshirilsin.",
                    code=card.code, spent=spent, cost=line_cost,
                ))
            balance = locked_points.get(card.id, 0.0)
            if float_compare(balance, spent, precision_digits=2) < 0:
                raise UserError(_(
                    "Vaucher %(code)s balansi yetarli emas: qoldiq %(balance)s, "
                    "so'ralgan %(spent)s. Vaucher boshqa kassada ishlatilgan bo'lishi mumkin.",
                    code=card.code, balance=balance, spent=spent,
                ))
