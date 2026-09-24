# -*- coding: utf-8 -*-
import base64
import secrets

from odoo import models


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    # ---- 58x40 birka o'lchamli vaucher (QR) uchun yordamchilar ----
    def _fz_qr_datauri(self):
        """QR ni INLINE base64 PNG qiladi (HTTP so'rovsiz — ko'p vaucher
        chiqarilganда wkhtmltopdf fayl-deskriptor chegarasidan oshmaydi)."""
        self.ensure_one()
        try:
            png = self.env["ir.actions.report"].sudo().barcode(
                "QR", self.code or "", width=220, height=220, quiet=1)
            if png:
                return "data:image/png;base64," + base64.b64encode(png).decode()
        except Exception:
            pass
        return ""

    def _fz_voucher_scale(self):
        """Vaucher qog'ozi (disable_shrinking bilan) 1:1 render bo'ladi —
        masshtab 1. Kerak bo'lsa `feliza.vaucher.masshtab` param bilan
        boshqariladi (kodni o'zgartirmasdan)."""
        p = self.env["ir.config_parameter"].sudo().get_param(
            "feliza.vaucher.masshtab")
        if p:
            try:
                return str(float(str(p).replace(",", ".")))
            except Exception:
                pass
        return "1"

    def _fz_voucher_amount(self):
        """Summani '500 000 so'm' ko'rinishida (nbsp ISHLATMAYDI)."""
        self.ensure_one()
        return "{:,.0f}".format(self.points or 0.0).replace(",", " ") + " so'm"

    def _generate_code(self):
        """Faqat raqamlardan iborat kod: "044" + 10 ta tasodifiy raqam (13 belgi).

        Standart kod ("044" + uuid bo'lagi, masalan 0442-e9e6-4033) ichida
        defis va lotin harflari bor. Skaner klaviatura sifatida ishlaydi va
        klaviatura tartibi (layout) boshqa tilda turganda "-" o'rniga "/"
        yuboradi, harflar ham buzilishi mumkin. Raqamlar barcha layout'larda
        bir xil. "044" prefiksi POS'ning "Coupon & Gift Card Barcodes"
        qoidasiga (pattern 043|044) mos kelishi uchun saqlanadi.
        """
        for _ in range(20):
            code = "044" + "".join(secrets.choice("0123456789") for _ in range(10))
            if not self.sudo().search_count([("code", "=", code)], limit=1):
                return code
        # Deyarli imkonsiz holat - standartga qaytamiz
        return super()._generate_code()
