import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Shu maydonlardan biri o'zgarsa - shablonga tegishli barcha variantlar
# Feliza'ga qayta yuboriladi (yoki arxivlanadi).
TRACKED_TEMPLATE_FIELDS = {
    "name", "list_price", "active", "x_publish_web",
    "description_sale", "categ_id", "x_name_ru",
}


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_publish_web = fields.Boolean(
        string="Saytga chiqarish",
        default=False,
        tracking=True,
        help="Belgilansa, mahsulot variantlari Feliza saytiga (moderatsiya "
             "uchun) yuboriladi. Belgi olib tashlansa yoki mahsulot "
             "arxivlansa, sayt uni avtomatik yashiradi.",
    )
    x_name_ru = fields.Char(string="Ruscha nom")
    x_brand = fields.Char(
        string="Brend",
        help="AI operator katalog API'si uchun. Bo'sh bo'lsa API'da null "
             "qaytadi - to'ldirilishi shart emas, keyinroq to'ldirilsa "
             "avtomatik ko'rinadi.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        for template in templates:
            if template.x_publish_web:
                template._feliza_push_variants()
        return templates

    def write(self, vals):
        result = super().write(vals)

        touched = TRACKED_TEMPLATE_FIELDS & set(vals.keys())
        if not touched:
            return result

        for template in self:
            went_unpublished = (
                ("active" in vals and not template.active)
                or ("x_publish_web" in vals and not template.x_publish_web)
            )
            if went_unpublished:
                template._feliza_push_variants_archive()
            elif template.active and template.x_publish_web:
                template._feliza_push_variants()

        return result

    def _feliza_push_variants(self):
        for variant in self.product_variant_ids:
            variant._feliza_push_upsert()

    def _feliza_push_variants_archive(self):
        for variant in self.product_variant_ids:
            variant._feliza_push_archive(reason="unpublished_or_archived_in_odoo")
