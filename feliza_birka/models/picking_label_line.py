# -*- coding: utf-8 -*-
"""BIRKA QATORI

Hujjatdagi har bir tovar uchun bitta qator: nechta birka chop etiladi,
narxi qancha, chegirmadami.

Narx va chegirma AVTOMAT to'ladi (mahsulot narxi + POS aksiyalari), lekin
qo'lda o'zgartirsa ham bo'ladi — hayotda har doim ham tizimdagidek
bo'lmaydi, xodim qulflanib qolmasligi kerak.
"""
import html as _html

from markupsafe import Markup

from odoo import api, fields, models


def _ascii_safe(text):
    """Matnni HTML belgilariga aylantiradi: «кора» -> «&#1082;&#1086;...».

    NEGA KERAK: birka PDF'ini `wkhtmltopdf` chizadi. U sahifa kodlashini
    faylning birinchi kilobaytiga qarab aniqlaydi, Odoo esa `<meta
    charset="utf-8">` ni uzun CSS/JS havolalaridan KEYIN qo'yadi — natijada
    kirill harflari «Ð¨Ð¾Ñ‚» bo'lib chiqadi. Sinovda aynan shunday bo'ldi.

    Matnni ASCII belgilarga aylantirsak, kodlash umuman ahamiyatsiz bo'ladi
    va birka har qanday serverda to'g'ri chiqadi.
    """
    if not text:
        return Markup("")
    return Markup(_html.escape(str(text))
                  .encode("ascii", "xmlcharrefreplace").decode("ascii"))


class FelizaPickingLabel(models.Model):
    _name = "feliza.picking.label"
    _description = "Chop etiladigan birka"
    _order = "id"

    picking_id = fields.Many2one(
        "stock.picking", required=True, ondelete="cascade", index=True)
    product_id = fields.Many2one(
        "product.product", string="Tovar", required=True)
    qty = fields.Integer(string="Birka soni", default=1)

    barcode = fields.Char(related="product_id.barcode", readonly=True)
    artikul = fields.Char(
        string="Artikul", compute="_compute_feliza_info", readonly=True)
    color = fields.Char(
        string="Rang", compute="_compute_feliza_info", readonly=True)
    size = fields.Char(
        string="O'lcham", compute="_compute_feliza_info", readonly=True)

    price = fields.Float(
        string="Narx", digits="Product Price",
        compute="_compute_price", store=True, readonly=False)
    discount_pct = fields.Float(
        string="Chegirma %", compute="_compute_price", store=True,
        readonly=False)
    old_price = fields.Float(
        string="Chegirmasiz narx", digits="Product Price",
        compute="_compute_price", store=True, readonly=False,
        help="To'ldirilgan bo'lsa birka SARIQ chiqadi va bu narx "
             "chizilgan holda ko'rsatiladi.")

    # ------------------------------------------------------------------ #
    @api.depends("product_id")
    def _compute_feliza_info(self):
        for line in self:
            p = line.product_id
            line.artikul = p.default_code or p.product_tmpl_id.default_code or ""
            color = size = ""
            for val in p.product_template_attribute_value_ids:
                aname = (val.attribute_id.name or "").strip().lower()
                if any(k in aname for k in ("rang", "цвет", "color")):
                    color = val.name
                elif any(k in aname for k in ("lcham", "размер", "size",
                                              "razmer")):
                    size = val.name
            line.color = color
            line.size = size

    @api.depends("product_id", "picking_id")
    def _compute_price(self):
        """Sotuv narxi va POS aksiyasidagi chegirma."""
        by_picking = {}
        for line in self:
            by_picking.setdefault(line.picking_id, []).append(line)
        for picking, lines in by_picking.items():
            discounts = {}
            if picking:
                discounts = self.env["product.product"]._feliza_active_discounts(
                    pos_configs=picking._feliza_pos_configs())
            for line in lines:
                base = line.product_id.list_price or 0.0
                pct = discounts.get(line.product_id.id, 0.0)
                line.discount_pct = pct
                if pct:
                    line.old_price = base
                    line.price = round(base * (100.0 - pct) / 100.0, 2)
                else:
                    line.old_price = 0.0
                    line.price = base

    # ------------------------------------------------------------------ #
    def _feliza_label_data(self):
        """Birkaga chiqadigan tayyor qiymatlar."""
        self.ensure_one()
        p = self.product_id
        tmpl = p.product_tmpl_id
        country = ""
        if "x_studio_ishlab_chiqarilgan_davlat" in tmpl._fields:
            country = tmpl.x_studio_ishlab_chiqarilgan_davlat or ""
        if not country and "country_of_origin" in tmpl._fields \
                and tmpl.country_of_origin:
            country = tmpl.country_of_origin.code or tmpl.country_of_origin.name
        raw_name = (tmpl.name or p.name or "")
        return {
            "name": _ascii_safe(raw_name),
            "name_len": len(raw_name),
            "barcode": p.barcode or "",
            "artikul": _ascii_safe(self.artikul or ""),
            "color": _ascii_safe(self.color or ""),
            "size": _ascii_safe(self.size or ""),
            "country": _ascii_safe((country or "").strip()),
            "price": self.price or 0.0,
            "old_price": self.old_price or 0.0,
            "discount": bool(self.old_price and self.old_price > self.price),
            "barcode_img": self._fz_barcode_datauri(p.barcode or ""),
            "barcode_is_qr": self._fz_kod_turi() == "qr",
        }

    @api.model
    def _fz_product_label_data(self, product, price=None, old_price=0.0):
        """Birka ma'lumotini TO'G'RIDAN-TO'G'RI mahsulotdan quradi (picking
        qatorisiz — tovar kartasidan chop etish uchun). `_feliza_label_data`
        bilan bir xil natija."""
        tmpl = product.product_tmpl_id
        artikul = product.default_code or tmpl.default_code or ""
        color = size = ""
        for val in product.product_template_attribute_value_ids:
            aname = (val.attribute_id.name or "").strip().lower()
            if any(k in aname for k in ("rang", "цвет", "color")):
                color = val.name
            elif any(k in aname for k in ("lcham", "размер", "size",
                                          "razmer")):
                size = val.name
        country = ""
        if "x_studio_ishlab_chiqarilgan_davlat" in tmpl._fields:
            country = tmpl.x_studio_ishlab_chiqarilgan_davlat or ""
        if not country and "country_of_origin" in tmpl._fields \
                and tmpl.country_of_origin:
            country = tmpl.country_of_origin.code or tmpl.country_of_origin.name
        if price is None:
            price = product.list_price or 0.0
        raw_name = (tmpl.name or product.name or "")
        return {
            "name": _ascii_safe(raw_name),
            "name_len": len(raw_name),
            "barcode": product.barcode or "",
            "artikul": _ascii_safe(artikul or ""),
            "color": _ascii_safe(color or ""),
            "size": _ascii_safe(size or ""),
            "country": _ascii_safe((country or "").strip()),
            "price": price or 0.0,
            "old_price": old_price or 0.0,
            "discount": bool(old_price and old_price > price),
            "barcode_img": self._fz_barcode_datauri(product.barcode or ""),
            "barcode_is_qr": self._fz_kod_turi() == "qr",
        }

    def _fz_kod_turi(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            "feliza.birka.kod_turi", "bar")

    def _fz_barcode_datauri(self, value):
        """Barkodni INLINE (base64 PNG data-URI) qiladi.

        Sabab: `t-options widget=barcode` katta hujjatda har barkodni HTTP
        orqali (`/report/barcode/...`) yuklaydi -> 745 socket -> wkhtmltopdf
        QT `select()` ning FD_SETSIZE=1024 chegarasidan oshib qulaydi
        (xato -6 / -11). Inline base64 esa HTTP so'rovsiz -> istalgan
        miqdordagi birka muammosiz chiqadi."""
        import base64
        value = (value or "").strip()
        if not value:
            return ""
        Report = self.env["ir.actions.report"].sudo()
        if self._fz_kod_turi() == "qr":
            try:
                png = Report.barcode("QR", value, width=180, height=180,
                                     quiet=1)
                if png:
                    return "data:image/png;base64," + \
                        base64.b64encode(png).decode()
            except Exception:
                pass
        for sym in ("EAN13", "Code128"):
            try:
                png = Report.barcode(sym, value, width=440, height=70,
                                     humanreadable=0, quiet=1)
                if png:
                    return "data:image/png;base64," + \
                        base64.b64encode(png).decode()
            except Exception:
                continue
        return ""
