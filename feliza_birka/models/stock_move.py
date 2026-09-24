# -*- coding: utf-8 -*-
"""QABUL QILUVCHI OMBORDAGI QOLDIQ — hujjat qatorida

Omborchi do'konga tovar jo'natayotganda «u yerda bundan qancha bor?»
degan savolga javob kerak. Buning uchun har bir qatorda qabul qiluvchi
ombordagi hozirgi qoldiq ko'rsatiladi.

MUHIM: qoldiq TO'G'RIDAN-TO'G'RI SQL bilan o'qiladi, ORM bilan emas.
Sababi — `warehouse_transfer_custom_19v` modulida `stock.quant` ga
yozuv qoidasi (record rule) bor: xodim faqat o'ziga biriktirilgan
ombor qoldig'ini ko'radi. ORM orqali o'qisak, omborchiga do'kon
qoldig'i 0 bo'lib ko'rinardi — bu esa eng yomon xato: raqam bor,
lekin noto'g'ri.
"""
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    feliza_src_qty = fields.Float(
        string="Bizda",
        compute="_compute_feliza_dest_qty",
        digits="Product Unit",
        help="Shu tovardan JO'NATUVCHI omborda (hujjatdagi «Исходное "
             "местоположение») hozir qancha borligi.")

    feliza_src_name = fields.Char(
        string="Jo'natuvchi ombor",
        compute="_compute_feliza_dest_qty")

    feliza_dest_qty = fields.Float(
        string="Qabul qiluvchida",
        compute="_compute_feliza_dest_qty",
        digits="Product Unit",
        help="Shu tovardan qabul qiluvchi omborda (do'konda) hozir "
             "qancha borligi.")

    feliza_dest_name = fields.Char(
        string="Qabul qiluvchi ombor",
        compute="_compute_feliza_dest_qty")

    @api.depends("product_id", "picking_id", "picking_id.location_id",
                 "picking_id.location_dest_id")
    def _compute_feliza_dest_qty(self):
        # hujjat bo'yicha guruhlaymiz — har bir ombor uchun bitta so'rov
        by_picking = {}
        for move in self:
            move.feliza_src_qty = 0.0
            move.feliza_src_name = ""
            move.feliza_dest_qty = 0.0
            move.feliza_dest_name = ""
            if move.picking_id and move.product_id:
                by_picking.setdefault(move.picking_id, self.browse())

        Picking = self.env["stock.picking"]
        for picking in by_picking:
            moves = self.filtered(lambda m: m.picking_id == picking)
            pids = moves.product_id.ids

            # --- bizda (jo'natuvchi ombor) ---
            src = picking._feliza_source_warehouse()
            if src:
                qty = Picking._feliza_wh_qty(src, pids)
                for move in moves:
                    move.feliza_src_qty = qty.get(move.product_id.id, 0.0)
                    move.feliza_src_name = src.name or ""

            # --- do'konda (qabul qiluvchi ombor) ---
            dest = picking._feliza_target_warehouse()
            # bir xil ombor bo'lsa (ichki ko'chirish) — ikkinchi ustun
            # takrorlanmasin, 0 bo'lib turgani chalg'itmasin
            if dest and dest != src:
                qty = Picking._feliza_wh_qty(dest, pids)
                for move in moves:
                    move.feliza_dest_qty = qty.get(move.product_id.id, 0.0)
                    move.feliza_dest_name = dest.name or ""
            elif dest:
                for move in moves:
                    move.feliza_dest_qty = move.feliza_src_qty
                    move.feliza_dest_name = dest.name or ""
