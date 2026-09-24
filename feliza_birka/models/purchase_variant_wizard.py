# -*- coding: utf-8 -*-
"""ZAKUP OYNASIDA AVTO ARTIKUL VA BARKOD

`purchase_easy_variant` oynasida ikki yo'l bor:
    * mavjud mahsulotni tanlash   -> raqamga TEGILMAYDI
    * yangi mahsulot yaratish     -> artikul va barkodlar shu yerda beriladi

Nega aynan `action_next` ichida? Chunki mahsulot va uning variantlari
aynan o'sha bosqichda yaratiladi. Keyinroq (masalan buyurtmaga
qo'shilganda) qilsak, xodim variantlar jadvalida barkodsiz tovarlarni
ko'rib qolardi.
"""
import logging

from odoo import _, models

from .feliza_numbering import (PARAM_AUTO_ARTIKUL, PARAM_AUTO_BARCODE,
                               auto_on)

_logger = logging.getLogger(__name__)


class PurchaseVariantWizard(models.TransientModel):
    _inherit = "purchase.variant.wizard"

    def action_next(self):
        # yangi mahsulot yaratilyaptimi yoki mavjudi tanlanganmi —
        # super() chaqirilishidan OLDIN bilib olamiz
        creating = not self.product_tmpl_id
        res = super().action_next()
        if creating and self.product_tmpl_id:
            self._feliza_assign_codes(self.product_tmpl_id)
        return res

    def _feliza_assign_codes(self, tmpl):
        """Artikul — mahsulotga bitta, barkod — har bir variantga.

        Sozlamalarda avto berish o'chirilgan bo'lsa — hech narsa
        yozilmaydi, xodim qo'lda kiritadi.
        """
        Num = self.env["feliza.numbering"]
        tmpl = tmpl.sudo()

        # --- artikul: faqat bo'sh bo'lsa va avto yoqilgan bo'lsa -------
        if not tmpl.default_code and auto_on(self.env, PARAM_AUTO_ARTIKUL):
            # artikul KATEGORIYAGA qarab beriladi: sumka 6xxxxx,
            # atir 4xxxxx, kiyim 1xxxxx va h.k.
            code = Num.next_artikul(categ=tmpl.categ_id)
            self._feliza_write_artikul(tmpl, code)
            _logger.info("Feliza: artikul %s -> %s", code, tmpl.display_name)

        # --- barkod: barkodsiz variantlarga ----------------------------
        variants = tmpl.product_variant_ids.filtered(lambda p: not p.barcode)
        if variants and auto_on(self.env, PARAM_AUTO_BARCODE):
            codes = Num.next_barcodes(len(variants))
            for variant, bc in zip(variants, codes):
                variant.write({"barcode": bc})
            _logger.info("Feliza: %s ta barkod berildi (%s ... %s)",
                         len(codes), codes[0], codes[-1])

    @staticmethod
    def _feliza_write_artikul(tmpl, code):
        """Artikulni HAR BIR VARIANTGA va shablonga yozadi.

        NEGA IKKALASIGA HAM?
        --------------------
        Odoo'da `product.template.default_code` — hisoblanadigan maydon:
        u variantdan olinadi va mahsulotda BIR NECHTA variant bo'lsa
        BO'SHATIB qo'yiladi. Ya'ni faqat shablonga yozsak, variantlar
        ro'yxatida «Ички ҳавола» ustuni bo'sh qolardi — birka, POS va
        hisobotlarda artikul ko'rinmasdi.

        Feliza bazasidagi mavjud 9 895 ta variantda artikul aynan
        variantning o'zida turibdi (masalan bitta mahsulotning 9 ta
        variantida ham «106547»). Shuning uchun biz ham xuddi shunday
        qilamiz — eski va yangi tovarlar bir xil ko'rinishda bo'ladi.

        TARTIB MUHIM: avval variantlar, keyin shablon. Variantga yozilsa
        shablonning hisobi qayta ishlaydi va uni bo'shatib qo'yadi;
        shuning uchun shablonni oxirida yozamiz.
        """
        variants = tmpl.with_context(active_test=False).product_variant_ids
        bosh = variants.filtered(lambda p: not p.default_code)
        if bosh:
            bosh.write({"default_code": code})
        tmpl.invalidate_recordset(["default_code"])
        if tmpl.default_code != code:
            tmpl.write({"default_code": code})

    def _feliza_codes_summary(self):
        """Oynada ko'rsatish uchun qisqa xulosa."""
        tmpl = self.product_tmpl_id
        if not tmpl:
            return ""
        n = len(tmpl.product_variant_ids.filtered("barcode"))
        return _("Artikul: %(code)s · barkodli variant: %(n)s") % {
            "code": tmpl.default_code or "—", "n": n}
