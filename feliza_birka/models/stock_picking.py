# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    feliza_label_ids = fields.One2many(
        "feliza.picking.label", "picking_id", string="Birkalar")
    feliza_label_count = fields.Integer(
        string="Birka soni", compute="_compute_feliza_label_count")

    @api.depends("feliza_label_ids.qty")
    def _compute_feliza_label_count(self):
        for pick in self:
            pick.feliza_label_count = sum(
                int(l.qty or 0) for l in pick.feliza_label_ids)

    # ------------------------------------------------------------------ #
    #  Qabul qiluvchi ombor                                               #
    # ------------------------------------------------------------------ #
    def _feliza_warehouse_of(self, location):
        """Lokatsiya qaysi omborga tegishli."""
        if not location:
            return self.env["stock.warehouse"]
        path = location.parent_path or ""
        for w in self.env["stock.warehouse"].sudo().search([], order="id"):
            vp = w.view_location_id.parent_path or ""
            if vp and path.startswith(vp):
                return w
        return self.env["stock.warehouse"]

    def _feliza_target_warehouse(self):
        """Tovar QAYERGA ketyapti — «Склад-получатель».

        DIQQAT: `stock.picking.warehouse_id` — bu qabul qiluvchi EMAS.
        `warehouse_transfer_custom_19v` da u
        `related="picking_type_id.warehouse_id"`, ya'ni hujjatning O'Z
        (jo'natuvchi) ombori. Qabul qiluvchi esa alohida maydon —
        `destination_warehouse_id` («Qabul qiluvchi ombor»).
        Dastlab shu chalkashlik sabab do'kon qoldig'i 0 chiqqan edi.
        """
        self.ensure_one()
        if "destination_warehouse_id" in self._fields \
                and self.destination_warehouse_id:
            return self.destination_warehouse_id
        loc = self.location_dest_id
        return self._feliza_warehouse_of(loc)

    def _feliza_source_warehouse(self):
        """Tovar QAYERDAN chiqyapti — «Исходное местоположение» ombori.

        Omborchi uchun eng kerakli raqam shu: o'zida qancha bor, shunga
        qarab nechta jo'natishni hal qiladi.
        """
        self.ensure_one()
        if "source_warehouse_id" in self._fields and self.source_warehouse_id:
            return self.source_warehouse_id
        wh = self._feliza_warehouse_of(self.location_id)
        # lokatsiyadan topilmasa — operatsiya turining ombori
        return wh or self.picking_type_id.warehouse_id

    @api.model
    def _feliza_wh_qty(self, warehouse, product_ids):
        """{product_id: qoldiq} — ombor bo'yicha, to'g'ridan-to'g'ri SQL.

        Yozuv qoidalari (record rules) chetlab o'tiladi: omborchi boshqa
        do'kon qoldig'ini ko'rish huquqiga ega bo'lmasa ham, bu yerda
        raqam KERAK — u shu asosda nechta jo'natishni hal qiladi.
        """
        if not warehouse or not product_ids:
            return {}
        path = (warehouse.sudo().view_location_id.parent_path or "") + "%"
        self.env.cr.execute("""
            SELECT q.product_id, COALESCE(SUM(q.quantity), 0)
              FROM stock_quant q
              JOIN stock_location l ON l.id = q.location_id
             WHERE l.usage = 'internal'
               AND l.parent_path LIKE %s
               AND q.product_id = ANY(%s)
             GROUP BY 1
        """, (path, list(product_ids)))
        return {r[0]: float(r[1] or 0) for r in self.env.cr.fetchall()}

    def _feliza_pos_configs(self):
        """Qabul qiluvchi omborga tegishli POS'lar (chegirmani aniqlash uchun)."""
        self.ensure_one()
        wh = self._feliza_target_warehouse()
        if not wh:
            return self.env["pos.config"]
        return self.env["pos.config"].sudo().search([
            ("picking_type_id.warehouse_id", "=", wh.id)])

    # ------------------------------------------------------------------ #
    #  Birka bo'limi                                                      #
    # ------------------------------------------------------------------ #
    def action_feliza_labels_fill(self):
        """Hujjatdagi tovarlardan birka ro'yxatini tuzadi.

        Soni: tasdiqlangan hujjatda — haqiqatda jo'natilgan miqdor,
        aks holda — talab qilingan miqdor. Ya'ni omborchi nechta tovar
        jo'natgan bo'lsa, shuncha birka tayyor turadi.
        """
        for pick in self:
            pick.feliza_label_ids.unlink()
            vals = []
            for move in pick.move_ids:
                if not move.product_id:
                    continue
                qty = move.quantity if pick.state == "done" else (
                    move.quantity or move.product_uom_qty)
                qty = int(round(qty or 0))
                if qty <= 0:
                    continue
                vals.append((0, 0, {"product_id": move.product_id.id,
                                    "qty": qty}))
            pick.feliza_label_ids = vals
        return True

    def action_feliza_print_labels(self):
        self.ensure_one()
        if not self.feliza_label_ids:
            self.action_feliza_labels_fill()
        lines = self.feliza_label_ids.filtered(lambda l: l.qty > 0)
        if not lines:
            raise UserError(_("Chop etadigan birka yo'q — sonini kiriting."))
        missing = lines.filtered(lambda l: not l.product_id.barcode)
        if missing:
            raise UserError(_(
                "Bu tovarlarda barkod yo'q, birka chop etib bo'lmaydi:\n\n%s"
            ) % "\n".join(
                "· " + p.product_id.display_name for p in missing[:15]))
        return self.env.ref(
            "feliza_birka.action_report_feliza_label").report_action(self)

    def _feliza_label_scale(self):
        """Birkani chinakam 58 x 40 mm qilib chiqarish koeffitsiyenti.

        `wkhtmltopdf` ning QT'i PATCHLANMAGAN yig'malarida sahifa
        ichidagi `mm` o'lchamlari haqiqiy o'lchamining atigi ~0.769
        qismi bo'lib chiqadi: 52 mm lik barkod qog'ozda 40 mm bo'ladi,
        matn ham shuncha kichrayadi va birkaning pastida bo'sh oq joy
        qoladi. (Sinovda o'lchandi: 52 mm -> 40.0 mm, 40 mm -> 30.7 mm.
        `--dpi` va `--zoom` bu holatga TA'SIR QILMAYDI.)

        Patchlangan yig'mada esa `mm` bir ga bir chiqadi va hech qanday
        tuzatish kerak emas.

        Agar biror serverda baribir mos kelmasa, tizim parametridan
        (`feliza.birka.masshtab`) qo'lda koeffitsiyent berish mumkin —
        kodni o'zgartirish shart emas.
        """
        qolda = self.env["ir.config_parameter"].sudo().get_param(
            "feliza.birka.masshtab")
        if qolda:
            try:
                return str(float(str(qolda).replace(",", ".")))
            except (TypeError, ValueError):
                pass
        try:
            from odoo.addons.base.models.ir_actions_report import _wkhtml
            return "1" if _wkhtml().is_patched_qt else "1.3006"
        except Exception:      # kutilmagan versiya — xavfsiz variant
            return "1"

    def _feliza_label_rows(self):
        """Chop etish uchun tayyor qatorlar (har biri bitta birka).

        Katta hujjat bo'laklarga bo'linib chiqarilganda kontekstdagi
        `fz_off`/`fz_lim` bo'yicha faqat kerakli bo'lak qaytariladi."""
        self.ensure_one()
        rows = []
        for line in self.feliza_label_ids.filtered(lambda l: l.qty > 0):
            # Barkod/ma'lumot BIR MARTA generatsiya qilinadi, keyin nusxa
            # ko'chiriladi (qty marta qayta barkod chizmaymiz — tezroq).
            data = line._feliza_label_data()
            rows.extend([data] * int(line.qty))
        off = self.env.context.get("fz_off")
        if off is not None:
            lim = self.env.context.get("fz_lim") or len(rows)
            rows = rows[off:off + lim]
        return rows

    def _feliza_label_total(self):
        self.ensure_one()
        return sum(int(l.qty or 0)
                   for l in self.feliza_label_ids.filtered(lambda l: l.qty > 0))


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    # Bitta hujjatda nechta birkadan keyin BO'LAKLAB render qilinadi.
    # wkhtmltopdf/QT `select()` FD_SETSIZE=1024 chegarasi bor: har inline
    # rasm = 1 vaqtinchalik fayl, ~1000+ birka bo'lsa qulaydi. Shuning
    # uchun katta hujjatni bo'laklab chiqarib, PDF larni birlashtiramiz.
    FZ_LABEL_CHUNK = 200

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        name = report_ref if isinstance(report_ref, str) else \
            getattr(report_ref, "report_name", "")
        is_label = ("feliza_birka.report_feliza_label" in str(name)
                    or "feliza_birka.report_product_label" in str(name))
        if is_label and res_ids:
            # Hujjat modeli: picking birkasi yoki tovar-kartasi wizardi
            model = ("feliza.product.label.wizard"
                     if "report_product_label" in str(name)
                     else "stock.picking")
            pickings = self.env[model].browse(res_ids).exists()
            if len(pickings) == 1 and hasattr(pickings, "_feliza_label_total"):
                total = pickings._feliza_label_total()
                if total > self.FZ_LABEL_CHUNK:
                    from odoo.tools.pdf import merge_pdf
                    streams = []
                    for off in range(0, total, self.FZ_LABEL_CHUNK):
                        rep = self.with_context(
                            fz_off=off, fz_lim=self.FZ_LABEL_CHUNK)
                        pdf = super(IrActionsReport, rep)._render_qweb_pdf(
                            report_ref, res_ids=res_ids, data=data)[0]
                        streams.append(pdf)
                    return merge_pdf(streams), "pdf"
        return super()._render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data)
