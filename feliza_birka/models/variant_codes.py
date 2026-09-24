# -*- coding: utf-8 -*-
"""YANGI VARIANTGA ARTIKUL VA BARKOD — O'ZI QO'YILADI

MUAMMO
------
Zakup oynasida mahsulot yaratilganda artikul va barkodlar o'sha
paytdagi variantlarga beriladi. Keyinroq xodim mahsulotga YANGI RANG
yoki O'LCHAM qo'shsa, Odoo yangi variantni yaratadi — u esa bo'm-bo'sh
chiqadi: artikuli ham, barkodi ham yo'q. Natijada «Варианты товаров»
ro'yxatida bitta qator bo'sh turadi va o'sha tovarni kassada
skanerlab bo'lmaydi.

YECHIM
------
Yangi variant yaratilgan zahoti:
    * ARTIKUL — mahsulotning eng birinchi variantidan ko'chiriladi
      (buyurtmachi qoidasi: bitta mahsulot = bitta artikul);
    * BARKOD  — yangi va betakror qilib beriladi, chunki barkod
      har bir variantga o'ziniki bo'lishi kerak.

NEGA FAQAT «AKASI BOR» BO'LSA
-----------------------------
Agar mahsulotning birorta variantida ham artikul bo'lmasa, bu YANGI
mahsulot degani — uni zakup oynasi (`purchase_variant_wizard`) o'zi
raqamlaydi. Shu bosqichda aralashsak, bitta mahsulotga ikki marta
raqam berilib qolardi. Shuning uchun bu ilgak faqat mahsulotda
allaqachon artikulli variant BOR bo'lganda ishlaydi.

TEZLIK
------
Har bir shablon uchun bitta tekshiruv, barkodlar esa bitta so'rov
bilan olinadi. Oddiy import yoki ko'p tovar yaratishda ham qo'shimcha
yuk sezilmaydi.
"""
import logging

from odoo import api, models

from .feliza_numbering import (PARAM_AUTO_ARTIKUL, PARAM_AUTO_BARCODE,
                               auto_on)

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        try:
            records._feliza_yangi_variant_kodlari()
        except Exception:                                   # noqa: BLE001
            # Rang qo'shish HECH QACHON xatolik bilan to'xtamasin —
            # kod berilmasa ham tovar yaratilaveradi, xato esa logga
            # tushadi va keyin qo'lda to'g'rilanadi.
            _logger.exception(
                "Feliza: yangi variantga artikul/barkod berib bo'lmadi "
                "(variantlar: %s)", records.ids)
        return records

    # ------------------------------------------------------------------ #
    def _feliza_yangi_variant_kodlari(self):
        art_on = auto_on(self.env, PARAM_AUTO_ARTIKUL)
        bar_on = auto_on(self.env, PARAM_AUTO_BARCODE)
        if not (art_on or bar_on):
            return

        yangi = self.filtered(lambda p: p.product_tmpl_id)
        if not yangi:
            return

        barkodsiz = []
        for tmpl in yangi.mapped("product_tmpl_id"):
            aka = tmpl.with_context(active_test=False).product_variant_ids \
                .filtered(lambda p: p.default_code)
            if not aka:
                # yangi mahsulot — raqamni zakup oynasi beradi
                continue
            kod = aka.sorted("id")[0].default_code
            shu = yangi.filtered(lambda p: p.product_tmpl_id == tmpl)

            if art_on:
                bosh = shu.filtered(lambda p: not p.default_code)
                if bosh:
                    bosh.write({"default_code": kod})
                    _logger.info(
                        "Feliza: yangi variantga artikul %s berildi "
                        "(%s ta, mahsulot: %s)",
                        kod, len(bosh), tmpl.display_name)

            if bar_on:
                barkodsiz += shu.filtered(lambda p: not p.barcode).ids

        if barkodsiz:
            variantlar = self.browse(barkodsiz)
            kodlar = self.env["feliza.numbering"].next_barcodes(len(variantlar))
            for variant, bc in zip(variantlar, kodlar):
                variant.barcode = bc
            _logger.info("Feliza: %s ta yangi variantga barkod berildi (%s ... %s)",
                         len(kodlar), kodlar[0], kodlar[-1])
