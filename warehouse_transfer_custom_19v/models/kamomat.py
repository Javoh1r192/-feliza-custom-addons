# -*- coding: utf-8 -*-
"""KAMOMAT — DO'KONGA KAM YETIB BORGAN YUK

MUAMMO
------
Skladchi 10 dona jo'natadi, do'konda 8 dona chiqadi. Do'kon xodimi
qabulni tasdiqlaganda Odoo so'raydi: «Rezerv buyurtma yaratilsinmi?».
U «Yo'q» (No Backorder) desa, qolgan 2 dona TRANZIT lokatsiyasida
osilib qoladi: sklad hisobidan chiqib ketgan, do'konga ham kirmagan.
Hech kim buni ko'rmaydi — tovar shunchaki yo'qoladi.

YECHIM
------
Aynan o'sha «Yo'q» bosilgan payt tizim SKLADGA QAYTARISH hujjatini
o'zi yaratadi: tranzitdagi 2 dona -> skladning o'z omboriga. Skladchi
uni ochib ko'radi (qaysi Delivery, qaysi do'kon, qaysi tovar, qancha)
va oddiy «Validate» bilan qabul qilib oladi. Tovar hisobga qaytadi.

ARXITEKTURA — YANGI HISOB-KITOB YO'Q
------------------------------------
Qaytarish harakatlari `origin_returned_move_id` orqali asl Delivery
harakatiga bog'lanadi. Bu Odoo'ning STANDART mexanizmi va moduldagi
`_interwh_resolved_qty()` uni allaqachon hisobga oladi — ya'ni sklad
qaytarishni tasdiqlagach, Delivery'ning «Yo'lda» qoldig'i o'z-o'zidan
nolga tushadi. Hisobot mantiqiga bitta ham qator qo'shilmadi.

TEZLIK
------
Ilgak (`_action_done`) faqat kontekstda `cancel_backorder` bo'lganda
ishlaydi — ya'ni xodim aynan «Rezerv buyurtma kerak emas» tugmasini
bosganda (yoki operatsiya turi umuman backorder yaratmaydigan qilib
sozlangan bo'lsa). Qolgan barcha tasdiqlashlarda bu bitta lug'at
tekshiruvi — tizimga sezilarli yuk bermaydi.

XAVFSIZLIK
----------
Qaytarish hujjati yaratilmay qolsa ham DO'KONNING QABULI buzilmaydi:
xato faqat logga yoziladi. Do'kon xodimi hech qachon tushunarsiz
xatolik oynasini ko'rmaydi.
"""
import logging

from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

TRANZIT = "Inter Warehouse Transfer"


class StockPicking(models.Model):
    _inherit = "stock.picking"

    feliza_kamomat = fields.Boolean(
        string="Shortfall return",
        default=False,
        index=True,
        copy=False,
        help="Automatically created return: the shop received less than "
             "was sent and chose not to create a backorder.",
    )
    feliza_kamomat_receipt_id = fields.Many2one(
        "stock.picking",
        string="Short receipt",
        copy=False,
        index="btree_not_null",
        help="The shop receipt where the shortfall was detected.",
    )
    feliza_kamomat_delivery_id = fields.Many2one(
        "stock.picking",
        string="Original delivery",
        copy=False,
        index="btree_not_null",
        help="The delivery this shortfall belongs to.",
    )
    feliza_kamomat_shop_id = fields.Many2one(
        "stock.warehouse",
        string="Shop with shortfall",
        copy=False,
        index="btree_not_null",
    )

    # ------------------------------------------------------------------ #
    #  ILGAK                                                              #
    # ------------------------------------------------------------------ #
    def _action_done(self):
        res = super()._action_done()
        # `cancel_backorder` — Odoo aynan «rezerv buyurtma yaratilmasin»
        # deb tasdiqlanayotgan hujjatlar uchun qo'yadigan kontekst.
        if self.env.context.get("cancel_backorder"):
            nomzodlar = self.filtered(
                lambda p: p.picking_type_code == "incoming"
                and p.sudo().inter_wh_delivery_id
            )
            if nomzodlar:
                try:
                    nomzodlar._feliza_kamomat_yarat()
                except Exception:                       # noqa: BLE001
                    # Qaytarish hujjati yaratilmasa ham QABUL buzilmasin.
                    _logger.exception(
                        "Feliza kamomat: qaytarish hujjatini yaratib "
                        "bo'lmadi (hujjatlar: %s)", nomzodlar.ids)
        return res

    # ------------------------------------------------------------------ #
    def _feliza_kamomat_qoldiq(self, delivery):
        """Delivery bo'yicha hali HAL QILINMAGAN qoldiq.

        :return: [(delivery_move, qoldiq), ...] — har tovar uchun bitta.
        """
        Move = self.env["stock.move"].sudo()
        natija = []
        d_moves = delivery.sudo().move_ids.filtered(lambda m: m.state == "done")
        for product in d_moves.mapped("product_id"):
            tovar_moves = d_moves.filtered(lambda m, p=product: m.product_id == p)
            yuborilgan = sum(tovar_moves.mapped("quantity"))
            # qabul qilingan + allaqachon qaytarib olingan
            hal = tovar_moves[0]._interwh_resolved_qty(delivery, product)
            # yo'lga qo'yilgan, lekin hali tasdiqlanmagan qaytarishlar —
            # ikkinchi marta qaytarish hujjati yaratilmasligi uchun
            kutayotgan = sum(
                Move.search([
                    ("origin_returned_move_id", "in", tovar_moves.ids),
                    ("state", "not in", ("done", "cancel")),
                ]).mapped("product_uom_qty")
            )
            qoldiq = yuborilgan - hal - kutayotgan
            aniqlik = tovar_moves[0].product_uom.rounding or 0.001
            if float_compare(qoldiq, 0.0, precision_rounding=aniqlik) > 0:
                natija.append((tovar_moves[0], qoldiq))
        return natija

    def _feliza_kamomat_yarat(self):
        """Kam qabul qilingan yuk uchun skladga qaytarish hujjati."""
        Picking = self.env["stock.picking"].sudo()
        Move = self.env["stock.move"].sudo()
        tranzit = self.env["stock.location"].sudo().search(
            [("name", "=", TRANZIT), ("usage", "=", "internal")], limit=1)
        if not tranzit:
            _logger.warning("Feliza kamomat: «%s» lokatsiyasi topilmadi", TRANZIT)
            return

        for qabul in self:
            qabul = qabul.sudo()
            delivery = qabul.inter_wh_delivery_id
            if not delivery:
                continue

            manba_wh = delivery.picking_type_id.warehouse_id
            if not manba_wh or not manba_wh.lot_stock_id:
                continue

            qatorlar = self._feliza_kamomat_qoldiq(delivery)
            if not qatorlar:
                continue

            tur = self.env["stock.picking.type"].sudo().search(
                [("warehouse_id", "=", manba_wh.id), ("code", "=", "incoming")],
                limit=1)
            if not tur:
                _logger.warning(
                    "Feliza kamomat: «%s» omborida qabul turi yo'q",
                    manba_wh.name)
                continue

            dokon = qabul.picking_type_id.warehouse_id
            joy = manba_wh.lot_stock_id

            # DIQQAT: `source_warehouse_id` ATAYLAB to'ldirilmaydi —
            # aks holda modulning action_confirm() ilgagi bu hujjatni
            # «zayavka» deb o'ylab, do'kondan yangi Delivery yaratib
            # yuborardi.
            yangi = Picking.create({
                "picking_type_id": tur.id,
                "location_id": tranzit.id,
                "location_dest_id": joy.id,
                "origin": delivery.name,
                "feliza_kamomat": True,
                "feliza_kamomat_receipt_id": qabul.id,
                "feliza_kamomat_delivery_id": delivery.id,
                "feliza_kamomat_shop_id": dokon.id if dokon else False,
                "company_id": manba_wh.company_id.id,
            })
            for d_move, qoldiq in qatorlar:
                Move.create({
                    "picking_id": yangi.id,
                    "picking_type_id": tur.id,
                    "product_id": d_move.product_id.id,
                    "product_uom_qty": qoldiq,
                    "product_uom": d_move.product_uom.id,
                    "location_id": tranzit.id,
                    "location_dest_id": joy.id,
                    # STANDART bog'lanish — _interwh_resolved_qty() shu
                    # orqali qaytarilgan miqdorni o'zi hisobga oladi.
                    "origin_returned_move_id": d_move.id,
                    "company_id": manba_wh.company_id.id,
                    # ANIQLANGAN kamomat — o'zgarmas raqam. `product_uom_qty`
                    # keyinchalik skladchi qisman qabul qilsa kamayib
                    # ketishi mumkin, hisobot esa haqiqatda qancha kam
                    # chiqqanini ko'rsatishi kerak.
                    "feliza_kamomat_qty": qoldiq,
                })
            yangi.action_confirm()
            yangi.action_assign()
            try:
                # Markup — aks holda Odoo 19 chatterda <b> teglari matn
                # bo'lib ko'rinib qoladi.
                yangi.message_post(body=Markup(_(
                    "Created automatically: shop <b>%(shop)s</b> received "
                    "less than was sent and did not create a backorder."
                    "<br/>Delivery: %(delivery)s<br/>Shop receipt: %(receipt)s"
                )) % {
                    "shop": dokon.name if dokon else "-",
                    "delivery": delivery.name,
                    "receipt": qabul.name,
                })
            except Exception:                           # noqa: BLE001
                _logger.exception("Feliza kamomat: xabar yozilmadi")
            _logger.info(
                "Feliza kamomat: %s yaratildi (%s <- %s, %d qator)",
                yangi.name, manba_wh.name,
                dokon.name if dokon else "?", len(qatorlar))


class StockMove(models.Model):
    _inherit = "stock.move"

    feliza_kamomat = fields.Boolean(
        string="Shortfall",
        related="picking_id.feliza_kamomat",
        store=True,
        index=True,
    )
    feliza_kamomat_shop_id = fields.Many2one(
        related="picking_id.feliza_kamomat_shop_id",
        string="Shop with shortfall",
        store=True,
        index="btree_not_null",
    )
    feliza_kamomat_delivery_id = fields.Many2one(
        related="picking_id.feliza_kamomat_delivery_id",
        string="Original delivery",
        store=True,
        index="btree_not_null",
    )
    feliza_kamomat_receipt_id = fields.Many2one(
        related="picking_id.feliza_kamomat_receipt_id",
        string="Short receipt",
        store=False,
    )
    feliza_kamomat_qty = fields.Float(
        string="Shortfall quantity",
        digits="Product Unit of Measure",
        copy=False,
        help="How much was actually missing at the moment the shop "
             "confirmed the receipt. This number never changes, even if "
             "the warehouse later takes back only part of it.",
    )


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    feliza_kamomat_count = fields.Integer(
        string="Shortfall returns",
        compute="_compute_feliza_kamomat_count",
    )

    def _compute_feliza_kamomat_count(self):
        """Ombor kartochkasida «Kamomat: N» ko'rsatish uchun.

        Bitta guruhlangan so'rov — kartochkalar soni kam, shuning uchun
        Odoo'ning o'z count_picking_* maydonlaridan qimmatroq emas.
        """
        data = self.env["stock.picking"]._read_group(
            [("picking_type_id", "in", self.ids),
             ("feliza_kamomat", "=", True),
             ("state", "not in", ("done", "cancel"))],
            ["picking_type_id"], ["__count"])
        soni = {pt.id: c for pt, c in data}
        for rec in self:
            rec.feliza_kamomat_count = soni.get(rec.id, 0)

    def feliza_action_kamomat_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_ready")
        action["domain"] = [("picking_type_id", "=", self.id),
                            ("feliza_kamomat", "=", True),
                            ("state", "not in", ("done", "cancel"))]
        action["context"] = {"default_picking_type_id": self.id}
        action["name"] = _("Shortfall returns")
        return action
