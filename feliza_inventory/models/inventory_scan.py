# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FelizaInventoryScan(models.Model):
    """Har bir skan = bitta yozuv (append-only).

    Nima uchun: sanashda 'counted' ni bitta qatorda oshirib borish (UPDATE)
    ko'p skaner bir vaqtda ishlaganda to'qnashadi (REPEATABLE READ da
    SerializationFailure). Har skanni ALOHIDA INSERT qilsak, yozuvlar
    bir-biriga to'qnashmaydi — hech bir skan yo'qolmaydi. 'Sanalgan' =
    shu yozuvlarning yig'indisi.
    """
    _name = 'feliza.inventory.scan'
    _description = "Inventarizatsiya skani"
    _order = 'id desc'

    line_id = fields.Many2one('feliza.inventory.line', required=True,
                              ondelete='cascade', index=True)
    qty = fields.Float(default=1.0)
    user_id = fields.Many2one('res.users', "Kim", index=True,
                              default=lambda s: s.env.user)
    # Tez qidiruv/hisobot/jonli panel uchun (stored related)
    session_id = fields.Many2one('feliza.inventory.session', "Sessiya",
                                 related='line_id.session_id', store=True,
                                 index=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', "Joy",
                                  related='line_id.location_id', store=True)
    product_id = fields.Many2one('product.product', "Tovar",
                                 related='line_id.product_id', store=True)
    barcode = fields.Char("Barkod", related='product_id.barcode')
    default_code = fields.Char("Artikul", related='product_id.default_code')
    is_manual = fields.Boolean("Qo'lda tuzatish", default=False,
                               help="Qo'lda kiritilgan tuzatish yozuvi.")
    is_delete = fields.Boolean("O'chirildi", default=False,
                               help="Tovar sanog'i 0 ga tushirilib "
                                    "'o'chirildi' — audit yozuvi.")
    variant_info = fields.Char("Rang / O'lcham", compute='_compute_variant_info')

    def unlink(self):
        """Append-only: skan yozuvini BUTUNLAY o'chirib bo'lmaydi (audit
        yo'qolmasin). Tovarni "o'chirish" uchun sonini 0 ga tushiring
        ('✎ tuzatish') — bu 'Skan tarixi'да 'O'chirildi' yozuvi sifatida
        saqlanadi. (Qo'llangan sessiya yoki tizim cascade'iga tegmaymiz.)"""
        if not self.env.context.get('fz_allow_scan_unlink'):
            raise UserError(_(
                "Skan yozuvini o'chirib bo'lmaydi (append-only). "
                "Tovarni chiqarish uchun sonini 0 ga tushiring — '✎ tuzatish' "
                "orqali; u 'Skan tarixi'да 'O'chirildi' bo'lib saqlanadi."))
        return super().unlink()

    @api.depends('product_id')
    def _compute_variant_info(self):
        for rec in self:
            vals = rec.product_id.product_template_attribute_value_ids
            rec.variant_info = ", ".join(
                v.name for v in vals) if vals else ""
