# -*- coding: utf-8 -*-
import base64
import io
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:      # Odoo'ning o'z talablarida bor, lekin ehtiyot shart
    openpyxl = None


# --------------------------------------------------------------------------
#  Ustun nomlari. Billz eksporti rus tilida, lekin bir xil fayl turli
#  nom bilan kelishi mumkin — shuning uchun bir nechta variant qabul
#  qilinadi. Solishtirish kichik harfda va bo'shliqsiz bajariladi.
# --------------------------------------------------------------------------
BARCODE_HEADERS = [
    "баркод", "штрихкод", "штрих-код", "barcode", "barkod", "штрих код",
]
QTY_HEADERS = [
    "отправлено", "количество", "кол-во", "колво", "qty", "quantity",
    "soni", "dona", "miqdor", "принято",
]
CODE_HEADERS = ["артикул", "artikul", "код", "default_code", "sku"]
NAME_HEADERS = ["наименование", "название", "nomi", "name", "tovar", "товар"]


def _norm(v):
    """Ustun nomini solishtirishga tayyorlaydi."""
    return re.sub(r"\s+", " ", str(v or "").strip().lower())


def _clean_barcode(v):
    """Excel barkodni son qilib saqlab qo'yishi mumkin: 2.00000015e+12.

    Shuning uchun butun songa aylantirib, keyin matnga o'giramiz.
    """
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    s = str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s


def _to_qty(v):
    """«5», «5 », «1 234», «1,5» — hammasini songa aylantiradi."""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


class PickingImportWizard(models.TransientModel):
    _name = "feliza.picking.import.wizard"
    _description = "Hujjat qatorlarini Excel fayldan yuklash"

    picking_id = fields.Many2one(
        "stock.picking", string="Hujjat", required=True, ondelete="cascade")
    file = fields.Binary(string="Excel fayl", required=True, attachment=False)
    filename = fields.Char(string="Fayl nomi")
    mode = fields.Selection(
        [("add", "Mavjud qatorlarga qo'shilsin"),
         ("replace", "Mavjud qatorlar o'chirilib, yangisi yozilsin")],
        string="Rejim", default="add", required=True)

    state = fields.Selection(
        [("choose", "Fayl tanlash"), ("done", "Natija")],
        default="choose")
    result_html = fields.Html(string="Natija", readonly=True)
    missing_file = fields.Binary(string="Topilmaganlar (CSV)", readonly=True,
                                 attachment=False)
    missing_name = fields.Char(readonly=True)

    # ------------------------------------------------------------------ #
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get("picking_id") and self.env.context.get("active_model") \
                == "stock.picking":
            res["picking_id"] = self.env.context.get("active_id")
        return res

    # ------------------------------------------------------------------ #
    def _read_rows(self):
        """Fayldan (barkod -> dona) va yordamchi ma'lumot o'qiydi."""
        if openpyxl is None:
            raise UserError(_("Serverda «openpyxl» kutubxonasi yo'q."))
        try:
            content = base64.b64decode(self.file)
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        except Exception as e:
            raise UserError(
                _("Faylni o'qib bo'lmadi. .xlsx formatida ekaniga ishonch "
                  "hosil qiling.\n\n%s") % e)

        ws = wb.worksheets[0]

        # --- sarlavha qatorini topamiz (birinchi 10 qator ichida) --------
        head_row = cols = None
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=10,
                                             values_only=True), start=1):
            names = {_norm(c): j for j, c in enumerate(row) if c is not None}
            bc = next((names[n] for n in names if n in BARCODE_HEADERS), None)
            if bc is not None:
                head_row, cols = i, names
                break
        if cols is None:
            raise UserError(
                _("Faylda barkod ustuni topilmadi. Ustun nomi «Баркод», "
                  "«Штрихкод» yoki «Barcode» bo'lishi kerak."))

        i_bc = next(cols[n] for n in cols if n in BARCODE_HEADERS)
        i_qty = next((cols[n] for n in cols if n in QTY_HEADERS), None)
        if i_qty is None:
            raise UserError(
                _("Faylda soni ustuni topilmadi. Ustun nomi «Отправлено», "
                  "«Количество» yoki «Qty» bo'lishi kerak."))
        i_code = next((cols[n] for n in cols if n in CODE_HEADERS), None)
        i_name = next((cols[n] for n in cols if n in NAME_HEADERS), None)

        qty = {}
        info = {}
        rows = skipped = 0
        for row in ws.iter_rows(min_row=head_row + 1, values_only=True):
            if i_bc >= len(row):
                continue
            bc = _clean_barcode(row[i_bc])
            if not bc:
                continue
            rows += 1
            q = _to_qty(row[i_qty]) if i_qty < len(row) else 0.0
            if q <= 0:
                skipped += 1
                continue
            qty[bc] = qty.get(bc, 0.0) + q
            if bc not in info:
                info[bc] = (
                    str(row[i_code]).strip() if i_code is not None
                    and i_code < len(row) and row[i_code] is not None else "",
                    str(row[i_name]).strip() if i_name is not None
                    and i_name < len(row) and row[i_name] is not None else "",
                )
        wb.close()
        if not qty:
            raise UserError(_("Faylda soni musbat bo'lgan qator topilmadi."))
        return qty, info, rows, skipped

    # ------------------------------------------------------------------ #
    def action_import(self):
        self.ensure_one()
        picking = self.picking_id
        if not picking:
            raise UserError(_("Hujjat topilmadi."))
        if picking.state in ("done", "cancel"):
            raise UserError(
                _("Hujjat holati «%s» — qator qo'shib bo'lmaydi.")
                % picking.state)

        qty, info, rows, zero_rows = self._read_rows()

        # --- barkod -> mahsulot ------------------------------------------
        products = self.env["product.product"].with_context(
            active_test=False).search([("barcode", "in", list(qty))])
        by_bc = {p.barcode: p for p in products}

        missing = [b for b in qty if b not in by_bc]
        archived = [b for b, p in by_bc.items() if not p.active]

        if self.mode == "replace":
            picking.move_ids.filtered(
                lambda m: m.state not in ("done", "cancel")).unlink()

        vals = []
        added_q = 0.0
        for b, q in qty.items():
            p = by_bc.get(b)
            if not p or not p.active:
                continue
            vals.append((0, 0, {
                "product_id": p.id,
                "product_uom_qty": q,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
            }))
            added_q += q
        if vals:
            picking.write({"move_ids": vals})

        # --- natija -------------------------------------------------------
        html = [
            "<div>",
            "<p><b>Fayl:</b> %s</p>" % (self.filename or ""),
            "<ul>",
            "<li>Fayldagi qator: <b>%d</b>%s</li>" % (
                rows,
                (" (soni 0 bo'lgan %d qator o'tkazib yuborildi)" % zero_rows)
                if zero_rows else ""),
            "<li>Hujjatga qo'shildi: <b>%d</b> tovar / <b>%s</b> dona</li>"
            % (len(vals), ("%g" % added_q)),
        ]
        if missing:
            html.append("<li style='color:#b02020'>Bazada topilmadi: "
                        "<b>%d</b> barkod</li>" % len(missing))
        if archived:
            html.append("<li style='color:#b02020'>Arxivlangan tovar: "
                        "<b>%d</b> barkod — qo'shilmadi</li>" % len(archived))
        html.append("</ul>")

        bad = missing + [b for b in archived if b not in missing]
        if bad:
            html.append("<p><b>Qo'shilmagan barkodlar</b> "
                        "(birinchi 30 tasi, to'liq ro'yxat CSV faylda):</p>")
            html.append("<div style='max-height:340px;overflow:auto'>")
            html.append("<table class='table table-sm'><tr>"
                        "<th>Barkod</th><th>Artikul</th><th>Nomi</th>"
                        "<th>Dona</th><th>Sabab</th></tr>")
            for b in bad[:30]:
                code, name = info.get(b, ("", ""))
                why = "arxivlangan" if b in archived else "bazada yo'q"
                html.append("<tr><td>%s</td><td>%s</td><td>%s</td>"
                            "<td>%g</td><td>%s</td></tr>"
                            % (b, code, name, qty.get(b, 0), why))
            html.append("</table></div>")

            csv = "barkod;artikul;nomi;dona;sabab\n"
            for b in bad:
                code, name = info.get(b, ("", ""))
                why = "arxivlangan" if b in archived else "bazada yo'q"
                csv += "%s;%s;%s;%g;%s\n" % (b, code, name, qty.get(b, 0), why)
            self.missing_file = base64.b64encode(csv.encode("utf-8-sig"))
            self.missing_name = "topilmagan_barkodlar.csv"
        html.append("</div>")

        self.state = "done"
        self.result_html = "".join(html)
        return {
            "type": "ir.actions.act_window",
            "name": _("Excel'dan tovar yuklash — natija"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    def action_close(self):
        return {"type": "ir.actions.act_window_close"}
