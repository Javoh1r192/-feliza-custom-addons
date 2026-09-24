import logging

from odoo import models, fields, api

from .feliza_webhook_client import to_feliza_datetime

_logger = logging.getLogger(__name__)

# Variant darajasidagi shu maydonlar o'zgarsa ham qayta yuboriladi
# (shablon darajasidagi maydonlar product_template.py'da kuzatiladi).
TRACKED_VARIANT_FIELDS = {"barcode", "default_code", "active"}


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)

        for product in products:
            if product.product_tmpl_id.x_publish_web and product.active:
                product._feliza_push_upsert()

        return products

    def write(self, vals):
        result = super().write(vals)

        touched = TRACKED_VARIANT_FIELDS & set(vals.keys())
        if touched:
            for product in self:
                if "active" in vals and not product.active:
                    product._feliza_push_archive(reason="archived_in_odoo")
                elif product.active and product.product_tmpl_id.x_publish_web:
                    product._feliza_push_upsert()

        return result

    # ---------------------------------------------------------------
    # Feliza webhook: products-upsert / products-archive
    # ---------------------------------------------------------------

    def _feliza_online_warehouse(self):
        return self.env["stock.warehouse"].sudo().search([
            ("name", "=", "Online Ombor")
        ], limit=1)

    def _build_feliza_upsert_item(self):
        self.ensure_one()

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        warehouse = self._feliza_online_warehouse()
        stock_qty = 0
        if warehouse:
            stock_qty = self.with_context(warehouse_id=warehouse.id).free_qty

        variant_attributes = [
            {
                "name": ptav.attribute_id.name,
                "value": ptav.product_attribute_value_id.name,
            }
            for ptav in self.product_template_attribute_value_ids
        ]

        images = []
        if self.image_1920:
            images.append(f"{base_url}/web/image/product.product/{self.id}/image_1920")

        return {
            "odoo_template_id": self.product_tmpl_id.id,
            "odoo_variant_id": self.id,
            # API'ning qolgan qismi variant ID'ni "externalId" deb ataydi -
            # webhookda ham bir xil nom bilan takroran yuboramiz (backend
            # xohlagan kalitini saqlab boradi).
            "externalId": self.id,
            "sku": self.default_code or None,
            "barcode": self.barcode or None,
            "name_uz": self.with_context(lang="uz_UZ").name,
            # Feliza backend name_ru bo'sh bo'lsa productni yaratishni rad
            # etadi (401 qaytaradi). 16000+ mahsulotni qo'lda tarjima qilish
            # imkonsiz, shuning uchun tarjima qilinmagan bo'lsa o'zbekcha
            # nomni zaxira sifatida yuboramiz - haqiqiy tarjima qo'shilsa
            # (x_name_ru to'ldirilsa), o'sha ustunlik qiladi.
            "name_ru": self.product_tmpl_id.x_name_ru or self.with_context(lang="uz_UZ").name,
            "variant_attributes": variant_attributes,
            "price": self.lst_price,
            "sale_price": None,
            "sale_from": None,
            "sale_to": None,
            "stock_qty": int(stock_qty),
            "odoo_category": self.categ_id.complete_name or None,
            "images": images,
            "description_base": self.product_tmpl_id.description_sale or None,
            "is_active": self.active,
            "odoo_updated_at": to_feliza_datetime(self.write_date),
        }

    def _feliza_push_upsert(self):
        self.ensure_one()
        self.with_delay(
            identity_key=f"feliza-products-upsert-{self.id}",
            description=f"Feliza products-upsert: variant {self.id}",
        )._feliza_send_upsert()

    def _feliza_push_archive(self, reason=None):
        self.ensure_one()
        self.with_delay(
            description=f"Feliza products-archive: variant {self.id}",
        )._feliza_send_archive(reason)

    def _feliza_send_upsert(self):
        self.ensure_one()
        payload = {"items": [self._build_feliza_upsert_item()]}
        self.env["feliza.webhook.client"].post("/products-upsert", payload)

    def _feliza_send_archive(self, reason=None):
        self.ensure_one()
        payload = {"odoo_variant_id": self.id, "externalId": self.id}
        if reason:
            payload["reason"] = reason
        self.env["feliza.webhook.client"].post("/products-archive", payload)

    # ---------------------------------------------------------------
    # Feliza webhook: stock-updated
    # ---------------------------------------------------------------

    def _feliza_push_stock_updated(self, reason=None):
        """`self` bir nechta mahsulotni o'z ichiga olishi mumkin - hammasi
        BITTA stock-updated so'rovida (changes[] massivi) yuboriladi."""
        if not self:
            return
        self.with_delay(
            description=f"Feliza stock-updated: {len(self)} ta variant",
        )._feliza_send_stock_updated(reason)

    def _feliza_send_stock_updated(self, reason=None):
        warehouse = self._feliza_online_warehouse()
        now = to_feliza_datetime(fields.Datetime.now())

        changes = []
        for product in self:
            stock_qty = 0
            if warehouse:
                stock_qty = product.with_context(warehouse_id=warehouse.id).free_qty
            changes.append({
                "odoo_variant_id": product.id,
                "externalId": product.id,
                "stock_qty": int(stock_qty),
                "changed_at": now,
            })

        if not changes:
            return

        payload = {"changes": changes}
        if reason:
            payload["reason"] = reason
        if warehouse:
            payload["warehouse"] = warehouse.name

        self.env["feliza.webhook.client"].post("/stock-updated", payload)