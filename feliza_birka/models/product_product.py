# -*- coding: utf-8 -*-
"""CHEGIRMANI POS «SKIDKI I LOYALNOST» DAN O'QISH

Buyurtmachi: «skidkadagi tovarlarni shu yerdan olish kerak» —
POS → Tovarlar → Скидки и лояльность (`loyalty.program`).

Odoo'da chegirma shunday tuzilgan:
    loyalty.program  — dastur (masalan «15 % chegirma», turi «Акции»)
      └── loyalty.reward — mukofot: nechi foiz va QAYSI tovarlarga
      └── loyalty.rule   — shart: qaysi tovar sotilganda ishga tushadi

Birka uchun bizga «qaysi tovar va necha foiz» kerak, shuning uchun
mukofotdagi (`reward`) tovar ro'yxatiga qaraymiz. Mukofot butun
buyurtmaga (`order`) yoki eng arzon tovarga (`cheapest`) berilgan
bo'lsa — bu bitta tovarning birkasiga aloqador emas, o'tkazib
yuboriladi (aks holda hamma birka sariq bo'lib ketardi).

Do'kon ham hisobga olinadi: dastur ma'lum POS'larga biriktirilgan
bo'lsa, faqat o'sha do'konga ketayotgan tovar sariq birka oladi.
"""
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _feliza_active_discounts(self, pos_configs=None, date=None):
        """Amaldagi foizli chegirmalar xaritasi: {product_id: foiz}.

        Bir marta hisoblanadi va butun birka to'plamiga ishlatiladi —
        har bir tovar uchun alohida so'rov yubormaymiz.
        """
        date = date or fields.Date.context_today(self)
        Program = self.env["loyalty.program"].sudo()

        programs = Program.search([
            ("active", "=", True),
            ("pos_ok", "=", True),
            ("program_type", "=", "promotion"),
        ])
        result = {}
        for prog in programs:
            # --- muddat ---
            if prog.date_from and prog.date_from > date:
                continue
            if prog.date_to and prog.date_to < date:
                continue
            # --- do'kon ---
            prog_pos = prog.pos_config_ids if "pos_config_ids" in prog._fields \
                else self.env["pos.config"]
            if prog_pos and pos_configs is not None:
                if not (set(prog_pos.ids) & set(pos_configs.ids)):
                    continue

            for rw in prog.reward_ids:
                if rw.reward_type != "discount":
                    continue
                if rw.discount_mode != "percent":
                    continue
                if rw.discount_applicability != "specific":
                    # butun buyurtmaga / eng arzon tovarga — birkaga tegishli emas
                    continue
                pct = rw.discount or 0.0
                if pct <= 0:
                    continue
                for product in self._feliza_reward_products(rw):
                    if pct > result.get(product.id, 0.0):
                        result[product.id] = pct
        return result

    @api.model
    def _feliza_reward_products(self, reward):
        """Mukofot qaysi tovarlarga tegishli — ro'yxat, kategoriya, teg, domen."""
        Product = self.env["product.product"].sudo()
        products = Product.browse()

        if reward.discount_product_ids:
            products |= reward.discount_product_ids
        if reward.discount_product_category_id:
            products |= Product.search([
                ("categ_id", "child_of", reward.discount_product_category_id.id)])
        if reward.discount_product_tag_id:
            products |= Product.search([
                ("all_product_tag_ids", "in", reward.discount_product_tag_id.id)])
        dom = reward.discount_product_domain
        if dom and dom not in ("[]", "null", False):
            try:
                from odoo.tools.safe_eval import safe_eval
                products |= Product.search(safe_eval(dom))
            except Exception:
                pass
        return products
