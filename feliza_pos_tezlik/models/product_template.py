# -*- coding: utf-8 -*-
"""Kassa ochilishidagi N+1 so'rovni yo'q qiladi.

Asl `_add_archived_combinations` yuklanadigan har bir shablon uchun
`_get_attribute_exclusions()` ni chaqiradi, u esa `ensure_one()` bilan
ishlagani uchun har safar yangi SQL so'rov yuboradi. Feliza'da bu
~4 600 so'rov va ~10 soniya degani.

Bu yerdagi variant bir xil natijani guruhlab hisoblaydi.
"""
from collections import defaultdict

from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _add_archived_combinations(self, products):
        """Arxivlangan kombinatsiyalarni barcha shablonlar uchun birdan hisoblaydi.

        Chiqadigan natija asl metod bilan aynan bir xil bo'lishi shart —
        `_archived_combinations` kalitining mazmuni o'zgarmaydi.
        """
        product_data = {p["id"]: p for p in products}
        if not product_data:
            return
        tmpls = self.browse(product_data.keys())

        # 1) Shu shablonlarga tegishli barcha istisnolar — bitta qidiruv
        exclusions = self.env["product.template.attribute.exclusion"].search(
            [("product_tmpl_id", "in", tmpls.ids)]
        )
        exclusions.mapped("value_ids")
        exclusions.mapped("product_template_attribute_value_id")
        exclusions_by_tmpl = defaultdict(list)
        for exclusion in exclusions:
            exclusions_by_tmpl[exclusion.product_tmpl_id.id].append(exclusion)

        # 2) Barcha variantlar, arxivlangani bilan — bitta qidiruv
        variants = (
            self.env["product.product"]
            .with_context(active_test=False)
            .search([("product_tmpl_id", "in", tmpls.ids)])
        )
        variants.mapped("product_template_attribute_value_ids")
        variants_by_tmpl = defaultdict(lambda: ([], []))  # (faol, arxivlangan)
        for variant in variants:
            variants_by_tmpl[variant.product_tmpl_id.id][0 if variant.active else 1].append(variant)

        # 3) Atribut qiymatlarini oldindan yuklab qo'yish
        tmpls.mapped(
            "valid_product_template_attribute_line_ids.product_template_value_ids.ptav_active"
        )

        ptav_model = self.env["product.template.attribute.value"]
        for tmpl in tmpls:
            product = product_data[tmpl.id]

            # --- shablonning o'z istisnolari ---
            excluded_values = defaultdict(ptav_model.browse)
            for exclusion in exclusions_by_tmpl.get(tmpl.id, ()):
                ptav = exclusion.product_template_attribute_value_id
                if ptav:
                    excluded_values[ptav.id] |= exclusion.value_ids

            own_exclusions = {}
            for ptav in tmpl.valid_product_template_attribute_line_ids.product_template_value_ids:
                if not ptav.ptav_active:
                    continue
                values = excluded_values.get(ptav.id)
                own_exclusions[ptav.id] = values.filtered("ptav_active").ids if values else []
            all_exclusions = self._complete_inverse_exclusions(own_exclusions)

            # --- arxivlangan kombinatsiyalar ---
            active_variants, archived_variants = variants_by_tmpl.get(tmpl.id, ([], []))
            active_combinations = {
                tuple(v.product_template_attribute_value_ids.ids) for v in active_variants
            }
            archived_combinations = list(
                {
                    tuple(v.product_template_attribute_value_ids.ids)
                    for v in archived_variants
                    if v.product_template_attribute_value_ids
                    and all(p.ptav_active for p in v.product_template_attribute_value_ids)
                }
                - active_combinations
            )

            product["_archived_combinations"] = archived_combinations
            excluded = {}
            for ptav_id, ptav_ids in all_exclusions.items():
                for other_id in set(ptav_ids) - excluded.keys():
                    excluded[ptav_id] = other_id
            product["_archived_combinations"].extend(excluded.items())
