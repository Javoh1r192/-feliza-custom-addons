from odoo import models


class LoyaltyCard(models.Model):
    _inherit = "loyalty.card"

    def write(self, vals):
        result = super().write(vals)

        if "points" in vals:
            for card in self:
                if card.partner_id:
                    # cashback_balance qiymati _feliza_send_customer_updated
                    # ichida ijro payti qayta hisoblanadi (barcha kartalar
                    # bo'yicha), shu sababli bu yerda faqat push qilinsa
                    # kifoya.
                    card.partner_id._feliza_push_customer_updated()

        return result
