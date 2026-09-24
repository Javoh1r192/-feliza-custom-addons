# -*- coding: utf-8 -*-
import base64

from odoo import models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def _loc_qr_datauri(self):
        """Lokatsiya kodidan (barcode) INLINE QR (base64 PNG data-URI).

        Inline — HTTP so'rovsiz, wkhtmltopdf FD_SETSIZE muammosiga
        tushmaydi."""
        self.ensure_one()
        value = (self.barcode or self.name or "").strip()
        if not value:
            return ""
        try:
            png = self.env["ir.actions.report"].sudo().barcode(
                "QR", value, width=300, height=300, quiet=1)
            if png:
                return "data:image/png;base64," + base64.b64encode(png).decode()
        except Exception:
            pass
        return ""

    def _loc_label_scale(self):
        """wkhtmltopdf mm-xatosini to'g'rilash koeffitsiyenti (birka bilan
        bir xil): patchlanmagan QT `mm` ni ~0.769x qilib chiqaradi."""
        try:
            from odoo.addons.base.models.ir_actions_report import _wkhtml
            return "1" if _wkhtml().is_patched_qt else "1.3006"
        except Exception:
            return "1"
