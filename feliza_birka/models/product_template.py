# -*- coding: utf-8 -*-
"""ODDIY ODOO MAHSULOT KARTASIDAN AVTO ARTIKUL + BARKOD

Zakup oynasidagi bilan AYNAN bir xil raqamlash. Xodim oddiy Odoo'da yangi
mahsulot yaratsa, kartadagi «🏷 Artikul + Barkod generatsiya» tugmasini
bosganda:
  * artikul (default_code) — MAHSULOTGA bitta, KATEGORIYA seriyasidan
    (kiyim 1xxxxx, atir 4xxxxx, sumka 6xxxxx ...);
  * barkod — HAR BIR variantga, EAN-13 (13 xonali, nazorat raqami bilan).

QOIDALAR:
  * KATEGORIYA majburiy — usiz seriya (demak artikul) topilmaydi.
  * Faqat NOTO'G'RI/BO'SH qiymatlar qayta beriladi: artikul 6-xonali
    Feliza artikuli (>=100000) bo'lmasa yoki barkod 13-xonali bo'lmasa.
    To'g'ri (mavjud) artikul/barkodga TEGILMAYDI — navbat tartibi buzilmaydi.
  * Bir variantda to'g'ri artikul bo'lsa — boshqalariga O'SHA ko'chiriladi
    (yangi raqam berilmaydi): mahsulotga bitta artikul qoidasi.
"""
import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MIN_ARTIKUL = 100000   # Feliza artikuli 6 xonali (1xxxxx ... 7xxxxx)


def _digits(s):
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _valid_artikul(code):
    d = _digits(code)
    return bool(d) and int(d) >= MIN_ARTIKUL


def _valid_barcode(bc):
    return len(_digits(bc)) == 13


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_feliza_generate_codes(self):
        """Kartadagi tugma — artikul (kategoriya seriyasidan) + barkod."""
        Num = self.env["feliza.numbering"]
        results = []
        for tmpl in self:
            t = tmpl.sudo()
            variants = t.with_context(active_test=False).product_variant_ids

            # ---- ARTIKUL: mahsulotga bitta, kategoriya seriyasidan --------
            existing = variants.filtered(lambda v: _valid_artikul(v.default_code))
            if existing:
                # allaqachon to'g'ri artikul bor — o'shani ishlatamiz
                code = existing.sorted("id")[0].default_code
            else:
                if not t.categ_id:
                    raise UserError(_(
                        "«%s» — avval mahsulot KATEGORIYASINI tanlang.\n\n"
                        "Artikul kategoriya seriyasidan beriladi (kiyim "
                        "1xxxxx, atir 4xxxxx, sumka 6xxxxx ...). Kategoriyasiz "
                        "qaysi seriyadan berishni aniqlab bo'lmaydi."
                    ) % (t.name or _("Mahsulot")))
                code = Num.next_artikul(categ=t.categ_id)
            # shu artikul turmagan variantlarga yozamiz (soxta '1' ustidan ham)
            bosh = variants.filtered(lambda v: (v.default_code or "") != code)
            if bosh:
                bosh.write({"default_code": code})
            t.invalidate_recordset(["default_code"])
            if t.default_code != code:
                t.write({"default_code": code})

            # ---- BARKOD: har variantga, faqat 13-xonali EAN bo'lmaganiga ---
            bad = variants.filtered(lambda v: not _valid_barcode(v.barcode))
            if bad:
                codes = Num.next_barcodes(len(bad))
                for variant, bc in zip(bad, codes):
                    variant.write({"barcode": bc})

            nb = len(variants.filtered(lambda v: _valid_barcode(v.barcode)))
            results.append((code, nb))
            _logger.info("Feliza: generatsiya artikul=%s barkod=%s ta -> %s",
                         code, nb, t.display_name)

        # MUHIM: hech qanday action QAYTARMAYMIZ (None) — shunda Odoo kartani
        # AVTO-RELOAD qiladi va yangi artikul/barkod DARHOL ko'rinadi.
        # (display_notification qaytarsak, forma yangilanmay, maydonlar bo'sh
        #  ko'rinib qolardi.)
        return None


class ProductProduct(models.Model):
    """Variant (product.product) kartasidan ham shu tugma bosilishi mumkin —
    shablonga yo'naltiramiz (artikul mahsulotga bitta, barkod har variantga)."""
    _inherit = "product.product"

    def action_feliza_generate_codes(self):
        return self.product_tmpl_id.action_feliza_generate_codes()
