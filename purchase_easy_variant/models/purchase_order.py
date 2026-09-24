from odoo import models

CURRENCY_COUNTRY_MAP = {
    'CNY': 'Xitoy',
    'TRY': 'Turkiya',
    'USD': 'Amerika',
    'EUR': 'Yevropa',
    'GBP': 'Angliya',
    'KRW': 'Koreya',
    'UZS': "O'zbekiston",
}


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_open_variant_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Mahsulot qo'shish",
            'res_model': 'purchase.variant.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_order_id': self.id},
        }

    def _apply_currency_country(self):
        """Valyuta asosida mahsulotlarga davlatni yozadi"""
        for order in self:
            country_val = CURRENCY_COUNTRY_MAP.get(order.currency_id.name, '')
            if not country_val:
                continue
            if 'x_studio_ishlab_chiqarilgan_davlat' not in self.env['product.template']._fields:
                continue
            templates = order.order_line.mapped('product_id.product_tmpl_id')
            templates.sudo().write({'x_studio_ishlab_chiqarilgan_davlat': country_val})

    def write(self, vals):
        res = super().write(vals)
        if 'currency_id' in vals:
            self._apply_currency_country()
        return res

    def action_apply_currency_country(self):
        """Manual tugma — hozirgi valyutaga ko'ra davlatni qo'yadi"""
        self._apply_currency_country()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bajarildi',
                'message': f"Mahsulotlarga '{CURRENCY_COUNTRY_MAP.get(self.currency_id.name, '')}' yozildi",
                'type': 'success',
                'sticky': False,
            }
        }
