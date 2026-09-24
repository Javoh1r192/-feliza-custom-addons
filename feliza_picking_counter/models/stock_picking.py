# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # ------------------------------------------------------------------ #
    #  Hujjatdagi tovar hisoblagichi
    #
    #  MUHIM: store=False. Maydonlar bazaga yozilmaydi, shuning uchun
    #  stock.move har yozilganda qayta hisoblash triggeri ishlamaydi va
    #  POS/ombor operatsiyalari sekinlashmaydi. Qiymat faqat hujjat
    #  ochilganda (va tahrirlash paytida onchange orqali) hisoblanadi.
    #
    #  NEGA UMUMAN KERAK: Odoo qatorlarni sahifalaydi (1-40 / 49) va
    #  jadval ostidagi yig'indi faqat KO'RINIB TURGAN sahifani qo'shadi
    #  (web/.../list_renderer.js -> computeAggregates: `list.records`).
    #  Bu yerdagi hisob esa har doim barcha qatorlar bo'yicha.
    # ------------------------------------------------------------------ #

    feliza_line_count = fields.Integer(
        string="Qatorlar",
        compute="_compute_feliza_counter",
        help="Hujjatdagi tovar qatorlari soni (bekor qilinganlarsiz).",
    )
    feliza_demand_qty = fields.Float(
        string="Talab (dona)",
        compute="_compute_feliza_counter",
        digits="Product Unit of Measure",
        help="Barcha qatorlar bo'yicha so'ralgan jami dona.",
    )
    feliza_done_qty = fields.Float(
        string="Kiritilgan (dona)",
        compute="_compute_feliza_counter",
        digits="Product Unit of Measure",
        help="Barcha qatorlar bo'yicha haqiqatda kiritilgan jami dona.",
    )
    feliza_diff_qty = fields.Float(
        string="Farq (dona)",
        compute="_compute_feliza_counter",
        digits="Product Unit of Measure",
        help="Kiritilgan minus talab. 0 bo'lsa hujjat to'liq.",
    )

    @api.depends(
        "move_ids",
        "move_ids.state",
        "move_ids.product_uom_qty",
        "move_ids.quantity",
    )
    def _compute_feliza_counter(self):
        for picking in self:
            moves = picking.move_ids.filtered(lambda m: m.state != "cancel")
            demand = sum(moves.mapped("product_uom_qty"))
            done = sum(moves.mapped("quantity"))
            picking.feliza_line_count = len(moves)
            picking.feliza_demand_qty = demand
            picking.feliza_done_qty = done
            picking.feliza_diff_qty = done - demand
