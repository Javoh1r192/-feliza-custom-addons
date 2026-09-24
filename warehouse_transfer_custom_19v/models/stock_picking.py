# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    warehouse_id = fields.Many2one(
        related="picking_type_id.warehouse_id",
        string="Ombor",
        readonly=True,
        store=True,
    )

    destination_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Qabul qiluvchi ombor",
        copy=False,
        help="Agar bu tanlansa, mahsulot boshqa omborga tranzit orqali o'tkaziladi.",
    )

    source_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Yuboruvchi ombor",
        copy=False,
        domain="[('id', '!=', warehouse_id)]",
    )

    # ------------------------------------------------------------------ #
    #  Sudo-backed display fields                                          #
    #  These always show the warehouse name regardless of the current      #
    #  user's record-rule access to that warehouse.                        #
    # ------------------------------------------------------------------ #
    destination_warehouse_display = fields.Char(
        string="Qabul qiluvchi ombor",
        compute="_compute_warehouse_display_names",
        store=False,
    )
    source_warehouse_display = fields.Char(
        string="Yuboruvchi ombor",
        compute="_compute_warehouse_display_names",
        store=False,
    )

    @api.depends("destination_warehouse_id", "source_warehouse_id")
    def _compute_warehouse_display_names(self):
        """
        Read warehouse names via sudo so that the name is always visible on
        the picking form even when the current user does not have record-rule
        access to the referenced warehouse.
        """
        for rec in self:
            sudo_rec = rec.sudo()
            dest = sudo_rec.destination_warehouse_id
            rec.destination_warehouse_display = dest.name if dest else False
            src = sudo_rec.source_warehouse_id
            rec.source_warehouse_display = src.name if src else False

    # Zayavka (Receipt) va unga bog'liq Delivery o'rtasidagi aloqa
    inter_wh_delivery_id = fields.Many2one(
        "stock.picking",
        string="Bog'liq Delivery",
        copy=False,
    )

    # ------------------------------------------------------------------ #
    #  Business logic                                                      #
    # ------------------------------------------------------------------ #

    def action_confirm(self):
        """Mark as Todo bosilganda ishlaydi"""
        res = super(StockPicking, self).action_confirm()

        for picking in self:
            # Agar bu Kirim bo'lsa va Yuboruvchi ombor tanlangan bo'lsa -> Delivery yaratish
            # Himoya: allaqachon delivery bog'langan bo'lsa yoki bu backorder bo'lsa,
            # ikkinchi marta delivery yaratilmaydi.
            if (
                picking.picking_type_code == "incoming"
                and picking.sudo().source_warehouse_id
                and not picking.sudo().inter_wh_delivery_id
                and not picking.backorder_id
            ):
                picking._create_delivery_from_zayavka()

        return res

    def _create_delivery_from_zayavka(self):
        """
        Manba ombor uchun Delivery yaratish va uni Ready holatiga o'tkazish.

        Uses sudo() when searching picking types / locations that belong to a
        warehouse the current user may not have record-rule access to.
        """
        self.ensure_one()

        env_sudo = self.env["stock.location"].sudo()
        transit_location = env_sudo.search(
            [
                ("name", "=", "Inter Warehouse Transfer"),
                ("usage", "=", "internal"),
            ],
            limit=1,
        )

        source_wh = self.sudo().source_warehouse_id
        source_picking_type = (
            self.env["stock.picking.type"]
            .sudo()
            .search(
                [
                    ("warehouse_id", "=", source_wh.id),
                    ("code", "=", "outgoing"),
                ],
                limit=1,
            )
        )

        if not source_picking_type:
            raise ValidationError(
                _("%s ombori uchun 'Delivery' turi topilmadi.") % source_wh.name
            )

        delivery_vals = {
            "picking_type_id": source_picking_type.id,
            "location_id": source_picking_type.default_location_src_id.id,
            "location_dest_id": transit_location.id,
            "origin": self.name,
            "destination_warehouse_id": self.warehouse_id.id,
            "move_ids": [
                (
                    0,
                    0,
                    {
                        "description_picking": move.description_picking or move.product_id.display_name,
                        "product_id": move.product_id.id,
                        "product_uom_qty": move.product_uom_qty,
                        "product_uom": move.product_uom.id,
                        "location_id": source_picking_type.default_location_src_id.id,
                        "location_dest_id": transit_location.id,
                    },
                )
                for move in self.move_ids
            ],
        }

        delivery = self.env["stock.picking"].sudo().create(delivery_vals)
        self.inter_wh_delivery_id = delivery.id

        # Darhol tasdiqlash va zaxira qilish
        delivery.action_confirm()
        delivery.action_assign()

        sender_name = self.env.user.name or 'Nomalum'

        # Ombor nomini tekshirib olamiz (False chiqmasligi uchun)
        # Zayavka (Receipt) da destination_warehouse_id bo'sh bo'lishi mumkin,
        # shuning uchun o'zining warehouse_id maydonidan olamiz.
        wh_name = self.warehouse_id.name or self.destination_warehouse_id.name or "Ombor ko'rsatilmagan"

        # Xabar matni:
        message_body = _(
            "Sizga **%s** omboriga yuk yetkazib berish uchun so'rov kelib tushdi. "
            "So'rov raqami: **%s**. \n"
            "Delivery order raqami: **%s**. \n\n"
            "**So'rov yuborgan shaxs:** %s"
        ) % (wh_name, self.name, delivery.name, sender_name)

        # Yuboruvchi omborning (source_warehouse_id) mas'ul userlariga yuborish
        delivery._send_notification_to_users(self.source_warehouse_id, message_body)


    def button_validate(self):
        """Validatsiya mantiqlari"""
        for picking in self:
            # --- YANGI QO'SHILGAN SHART ---
            # Zayavka (Receipt) draft holatida bo'lsa, validate qilishni taqiqlash
            if picking.picking_type_code == 'incoming' and picking.source_warehouse_id and picking.state == 'draft':
                raise ValidationError(_(
                    "Ushbu zayavka hali 'Draft' holatida. "
                    "Avval 'Mark as Todo' tugmasini bosing!"
                ))
            # ------------------------------

            # 1. Manzilni tranzitga yo'naltirish
            dest_wh = picking.sudo().destination_warehouse_id
            if dest_wh and picking.picking_type_code == "outgoing":
                transit_loc = (
                    self.env["stock.location"]
                    .sudo()
                    .search(
                        [
                            ("name", "=", "Inter Warehouse Transfer"),
                            ("usage", "=", "internal"),
                        ],
                        limit=1,
                    )
                )
                if transit_loc:
                    picking.location_dest_id = transit_loc.id
                    for move in picking.move_ids:
                        move.location_dest_id = transit_loc.id

            # 2. Zayavka (Receipt) ni tekshirish
            linked_delivery = picking.sudo().inter_wh_delivery_id
            if picking.picking_type_code == "incoming" and linked_delivery:
                if linked_delivery.state != "done":
                    raise ValidationError(
                        _(
                            "Ushbu zayavkani qabul qila olmaysiz! "
                            "Avval yuboruvchi ombor yukni jo'natishi kerak."
                        )
                    )
                # Yuborilganidan ORTIQ qabul qilishni taqiqlash
                # (aks holda tranzit lokatsiya minusga tushib, zaxira buziladi)
                picking._check_over_receipt(linked_delivery)

        res = super(StockPicking, self).button_validate()

        for picking in self:
            # 3. Delivery tasdiqlanganda avtomatik Receipt yaratish
            dest_wh = picking.sudo().destination_warehouse_id
            if (
                    picking.state == "done"
                    and picking.picking_type_code == "outgoing"
                    and dest_wh
            ):
                is_zayavka_based = False
                existing_receipt = False
                if picking.origin:
                    existing_receipt = (
                        self.env["stock.picking"]
                        .sudo()
                        .search(
                            [
                                ("name", "=", picking.origin),
                                ("picking_type_code", "=", "incoming"),
                                ("source_warehouse_id", "!=", False),
                            ],
                            limit=1,
                        )
                    )
                    if existing_receipt:
                        is_zayavka_based = True

                if not is_zayavka_based:
                    self._create_inter_warehouse_receipt(picking)
                else:
                    # ZAYAVKA OQIMI: haqiqiy yuborilgan miqdorni zayavkaga
                    # qaytarib sinxronlash (kam/ko'p yuborilgan bo'lishi mumkin)
                    picking._sync_zayavka_receipt_quantities(existing_receipt)

        # 4. Omborlar aro tarqatish hisobotida bitta transfer bitta marta
        #    ko'rinishini ta'minlash (Delivery/Receipt ikkalasi ham
        #    ko'rinib, miqdor ikki baravar bo'lib qolmasligi uchun).
        self.filtered(lambda p: p.state == "done")._sync_interwh_report_status()

        return res

    def _sync_interwh_report_status(self):
        """
        Omborlar aro tarqatish hisobotida (stock.move.interwh_report_status /
        interwh_report_qty) har bir jismoniy transfer FAQAT BITTA marta,
        va HAR DOIM YAKUNIY HAQIQIY holat bilan ko'rinishini ta'minlaydi.

        Ikkita hodisani ushlaydi:

        A) Receipt 'done' bo'lishi (push yoki pull oqim, to'liq yoki qisman
           qabul qilish) -> Receipt tomoni "yetib bordi" deb belgilanadi,
           bog'liq Delivery'ning qoldig'i qayta hisoblanadi. Agar qoldiq
           qolgan bo'lsa (qisman qabul qilingan) - YUBORUVCHI (A) ombor
           mas'ullariga va Delivery'ni yaratgan foydalanuvchiga, hamda
           Delivery hujjatining o'z chatteriga kamomad haqida xabar
           yoziladi - shu orqali qaysi Delivery'dan "Return" qilish
           kerakligini tezroq topish mumkin.

        B) Delivery'ga "Return" qilinishi (masalan B "No Backorder" bilan
           kam qabul qilgach, A qolgan miqdorni tranzitdan qaytarib olsa)
           -> Odoo'ning o'z origin_returned_move_id bog'lanishi orqali bu
           aniqlanadi, va bog'liq Delivery'ning qoldig'i shunga mos qayta
           hisoblanadi ("qaytarildi" deb hisobga olinadi, "yo'lda" dan
           ayiriladi).

        Har ikkala holatda ham: yo'lda + yetib bordi + qaytarildi = yuborilgan.

        Eslatma: agar Delivery'ning o'zi ham backorder qilingan bo'lsa
        (bir nechta alohida Delivery yozuvi bo'lsa), faqat bevosita
        bog'langan Delivery'ning harakatlari qayta hisoblanadi - bu
        kamdan-kam uchraydigan chekka holat.
        """
        affected = {}  # {(delivery, product): trigger_picking}

        for picking in self:
            done_moves = picking.move_ids.filtered(lambda m: m.state == "done")
            if not done_moves:
                continue

            # A) Receipt qabul qilindi (push yoki pull oqim)
            delivery = picking.sudo().inter_wh_delivery_id
            if picking.picking_type_code == "incoming" and delivery:
                done_moves.sudo().write({"interwh_report_status": "arrived"})
                for move in done_moves:
                    move.sudo().interwh_report_qty = move.quantity
                for product in done_moves.mapped("product_id"):
                    affected[(delivery, product)] = picking

            # B) Bu - avval yuborilgan yukka "Return" (qaytarish)
            returned_moves = done_moves.filtered(lambda m: m.origin_returned_move_id)
            for move in returned_moves:
                orig_picking = move.origin_returned_move_id.picking_id.sudo()
                if orig_picking.picking_type_code == "outgoing" and orig_picking.destination_warehouse_id:
                    affected[(orig_picking, move.product_id)] = picking

        for (delivery, product), trigger_picking in affected.items():
            self._resync_delivery_outstanding(delivery, product, trigger_picking)

    def _resync_delivery_outstanding(self, delivery, product, trigger_picking=None):
        """Berilgan Delivery va mahsulot bo'yicha, hozirgi umumiy HAL
        QILINGAN (qabul qilingan + qaytarilgan) miqdorni qayta hisoblab,
        Delivery tomonidagi hisobot holatini ("yo'lda" qoldig'ini) va
        kerak bo'lsa kamomad haqida bildirishnomani yangilaydi.

        :param trigger_picking: bu qayta hisoblashga sabab bo'lgan Receipt
            yoki Return hujjati - xabar matnida ko'rsatish uchun (bo'lishi
            shart emas).
        """
        delivery_moves = delivery.sudo().move_ids.filtered(
            lambda m, p=product: m.product_id == p and m.state == "done"
        )
        if not delivery_moves:
            return

        sent = sum(delivery_moves.mapped("quantity"))
        resolved = delivery_moves[0]._interwh_resolved_qty(delivery, product)
        rounding = delivery_moves[0].product_uom.rounding or 0.001
        outstanding = sent - resolved

        # TUZATISH: `outstanding > rounding` -> nolga nisbatan solishtirish.
        # rounding = 1.0 bo'lgan bazada rosa 1 dona qoldiq yo'qolib ketardi.
        if float_compare(outstanding, 0.0, precision_rounding=rounding) > 0:
            delivery_moves[0].sudo().write(
                {"interwh_report_status": "in_transit", "interwh_report_qty": outstanding}
            )
            if len(delivery_moves) > 1:
                delivery_moves[1:].sudo().write(
                    {"interwh_report_status": False, "interwh_report_qty": 0.0}
                )

            # Kamomad haqida YUBORUVCHI (A) ombor mas'ullariga va Delivery'ni
            # yaratgan foydalanuvchiga xabar - Delivery hujjatining o'z
            # chatteriga yoziladi, shu orqali A tez orada "Return" qilish
            # kerakligini tushunadi.
            delivery_sudo = delivery.sudo()
            trigger_txt = (
                _(" (%s hujjati bo'yicha)") % trigger_picking.name if trigger_picking else ""
            )
            message_body = _(
                "Diqqat! Ushbu Delivery bo'yicha \"%s\" mahsulotidan hali "
                "hal qilinmagan qoldiq bor%s: yuborilgan %s, hozirgacha hal "
                "qilingan (qabul qilingan + qaytarilgan) %s, qolgan "
                "%s dona hali tranzitda kutilmoqda. "
                "Agar bu miqdor haqiqatda yetishmayotgan/topilmayotgan "
                "bo'lsa, ushbu Delivery hujjatidan 'Return' qilib "
                "qoldiqni qaytarib olishni ko'rib chiqing."
            ) % (product.display_name, trigger_txt, sent, resolved, outstanding)

            # 1.5 (KAMOMAT): agar tizim qaytarish hujjatini allaqachon
            # o'zi yaratgan bo'lsa, "Return qiling" deb aytish noto'g'ri
            # bo'ladi - o'sha hujjatning NOMINI aytamiz.
            kam = self.env["stock.picking"].sudo().search([
                ("feliza_kamomat_delivery_id", "=", delivery_sudo.id),
                ("state", "not in", ("done", "cancel")),
            ], limit=1)
            if kam:
                message_body = _(
                    "Diqqat! Ushbu Delivery bo'yicha \"%s\" mahsulotidan "
                    "kamomat aniqlandi%s: yuborilgan %s, hal qilingan %s, "
                    "qolgan %s dona. Qaytarish hujjati AVTOMAT yaratildi: "
                    "%s - uni qabul qilib olsangiz, tovar sklad hisobiga "
                    "qaytadi."
                ) % (product.display_name, trigger_txt, sent, resolved,
                     outstanding, kam.name)

            recipient_users = delivery_sudo.warehouse_id.allowed_user_ids
            creator = delivery_sudo.create_uid
            if creator:
                recipient_users |= creator
            try:
                delivery_sudo.message_post(
                    body=message_body,
                    subject=_("Kamomad: %s") % delivery_sudo.name,
                    partner_ids=recipient_users.mapped("partner_id").ids,
                    message_type="notification",
                    subtype_xmlid="mail.mt_comment",
                )
            except Exception as e:
                _logger.error("Kamomad bildirishnomasini yuborishda xato: %s", str(e))
        else:
            delivery_moves.sudo().write({"interwh_report_status": False, "interwh_report_qty": 0.0})


    @api.constrains("destination_warehouse_id", "picking_type_id")
    def _check_destination_warehouse(self):
        """O'z omboriga o'zi yubora olmasligi kerak"""
        for picking in self:
            dest_wh = picking.sudo().destination_warehouse_id
            src_wh = picking.picking_type_id.warehouse_id
            if dest_wh and src_wh == dest_wh:
                raise ValidationError(
                    _("Mahsulotni ayni shu omborning o'ziga yubora olmaysiz!")
                )

    def _create_inter_warehouse_receipt(self, picking, force=False):
        """
        Qabul qiluvchi ombor uchun avtomatik Receipt yaratish (Lotlar bilan).

        Everything that touches the destination warehouse is done via sudo()
        because the user who validates the delivery may not have record-rule
        access to the destination warehouse.

        :param force: True bo'lsa duplicate guard tekshirilmaydi (masalan,
            zayavka allaqachon yopilgach kelgan backorder yuk uchun
            qo'shimcha Receipt yaratish kerak bo'lganda).
        """
        # Duplicate guard
        if not force and picking.origin and self.env["stock.picking"].sudo().search(
            [
                ("name", "=", picking.origin),
                ("picking_type_code", "=", "incoming"),
            ],
            limit=1,
        ):
            return

        transit_location = (
            self.env["stock.location"]
            .sudo()
            .search(
                [
                    ("name", "=", "Inter Warehouse Transfer"),
                    ("usage", "=", "internal"),
                ],
                limit=1,
            )
        )

        dest_wh = picking.sudo().destination_warehouse_id
        dest_picking_type = (
            self.env["stock.picking.type"]
            .sudo()
            .search(
                [
                    ("warehouse_id", "=", dest_wh.id),
                    ("code", "=", "incoming"),
                ],
                limit=1,
            )
        )

        if not dest_picking_type:
            raise ValidationError(
                _("%s ombori uchun 'Receipt' turi topilmadi.") % dest_wh.name
            )

        receipt_vals = {
            "picking_type_id": dest_picking_type.id,
            "location_id": transit_location.id,
            "location_dest_id": dest_picking_type.default_location_dest_id.id,
            "origin": picking.name,
            # Push-oqimda ham (xuddi pull/zayavka oqimidagi kabi) Receipt'ni
            # uni "tug'dirgan" Delivery'ga bog'laymiz. Bu ikkala oqimni ham
            # simmetrik qiladi va hisobotlarda (real_source_warehouse_id)
            # "yuk qayerdan kelgani"ni aniqlashga imkon beradi.
            "inter_wh_delivery_id": picking.id,
            "move_ids": [],
        }

        for move in picking.move_ids:
            qty = move.quantity if hasattr(move, "quantity") else move.quantity_done
            if qty <= 0:
                qty = move.product_uom_qty

            move_line_vals = []
            for line in move.move_line_ids:
                move_line_vals.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_uom_id": line.product_uom_id.id,
                            "lot_id": line.lot_id.id,
                            "quantity": line.quantity
                            if hasattr(line, "quantity")
                            else line.qty_done,
                            "location_id": transit_location.id,
                            "location_dest_id": dest_picking_type.default_location_dest_id.id,
                        },
                    )
                )

            receipt_vals["move_ids"].append(
                (
                    0,
                    0,
                    {
                        "description_picking": move.description_picking or move.product_id.display_name,
                        "product_id": move.product_id.id,
                        "product_uom_qty": qty,
                        "product_uom": move.product_uom.id,
                        "location_id": transit_location.id,
                        "location_dest_id": dest_picking_type.default_location_dest_id.id,
                        "move_line_ids": move_line_vals,
                    },
                )
            )

        if receipt_vals["move_ids"]:
            new_receipt = self.env["stock.picking"].sudo().create(receipt_vals)
            new_receipt.action_confirm()
            new_receipt.action_assign()


            # Tasdiqlagan foydalanuvchi ismini olish
            sender_name = self.env.user.name

            # Xabar matni:
            message_body = _(
                "Sizga **%s** omboridan **%s** raqamli yuk yuborildi. "
                "Qabul qilib olishingizni so'raymiz! \n\n"
                "**Yuborgan shaxs:** %s"
            ) % (picking.warehouse_id.name, new_receipt.name, sender_name)

            # Qabul qiluvchi omborga bildirishnoma yuborish
            new_receipt._send_notification_to_users(picking.destination_warehouse_id, message_body)


    # ------------------------------------------------------------------ #
    #  Zayavka <-> Delivery miqdor sinxronizatsiyasi                       #
    # ------------------------------------------------------------------ #

    def _sync_zayavka_receipt_quantities(self, receipt):
        """
        Zayavka asosidagi Delivery validate bo'lganda zayavka (Receipt)
        miqdorlarini HAQIQIY yuborilgan miqdorga tenglashtirish:

        - Kam yuborilsa  -> zayavka miqdori kamayadi (5 so'raldi, 3 yuborildi -> 3)
        - Ko'p yuborilsa -> zayavka miqdori oshadi (5 so'raldi, 10 yuborildi -> 10)
        - Umuman yuborilmagan mahsulot -> zayavka qatori bekor qilinadi
        - Zayavkada yo'q, lekin yuborilgan mahsulot -> yangi qator qo'shiladi
        - Lot/serial raqamlari ham ko'chiriladi
        - Farq bo'lsa qabul qiluvchi ombor userlariga xabar yuboriladi

        `self` - validate qilingan Delivery, `receipt` - bog'liq zayavka.
        """
        self.ensure_one()
        receipt = receipt.sudo()
        # Asl zayavka nomi - delivery'ning origin maydonida saqlanadi.
        # Backorder deliverylar ham shu origin'ni meros qilib oladi.
        zayavka_name = self.origin or receipt.name

        # Zayavka allaqachon yopilgan bo'lsa (masalan, bu backorder delivery
        # bo'lib, asosiy qism avvalroq qabul qilingan):
        if receipt.state in ("done", "cancel"):
            anchor_delivery = receipt.inter_wh_delivery_id
            open_receipt = False
            if anchor_delivery:
                # Ochiq qolgan receipt-backorder bormi? Bo'lsa - o'shani sinxronlaymiz
                open_receipt = (
                    self.env["stock.picking"]
                    .sudo()
                    .search(
                        [
                            ("picking_type_code", "=", "incoming"),
                            ("inter_wh_delivery_id", "=", anchor_delivery.id),
                            ("state", "not in", ("done", "cancel")),
                        ],
                        limit=1,
                    )
                )
            if open_receipt:
                return self._sync_zayavka_receipt_quantities(open_receipt)
            # Aks holda qolgan yuk uchun alohida yangi Receipt yaratamiz,
            # aks holda yuk tranzitda 'egasiz' qolib ketadi.
            self._create_inter_warehouse_receipt(self, force=True)
            return

        transit_location = (
            self.env["stock.location"]
            .sudo()
            .search(
                [
                    ("name", "=", "Inter Warehouse Transfer"),
                    ("usage", "=", "internal"),
                ],
                limit=1,
            )
        )
        dest_location = receipt.picking_type_id.default_location_dest_id

        # 1. Butun delivery zanjiri (asosiy + backorderlar) bo'yicha
        #    haqiqiy yuborilgan miqdorlar va lot ma'lumotlari
        delivery_domain = [
            ("picking_type_code", "=", "outgoing"),
            ("state", "=", "done"),
            ("destination_warehouse_id", "!=", False),
        ]
        if zayavka_name:
            delivery_domain.append(("origin", "=", zayavka_name))
        else:
            delivery_domain.append(("id", "=", self.id))
        deliveries = self.env["stock.picking"].sudo().search(delivery_domain)

        delivered_qty = defaultdict(float)
        delivered_lines = defaultdict(list)
        for move in deliveries.move_ids:
            if move.state != "done":
                continue
            delivered_qty[move.product_id] += move.quantity
            delivered_lines[move.product_id].extend(move.move_line_ids)

        # Avvalgi (done) receiptlar orqali qabul qilib bo'lingan miqdorlarni ayiramiz
        received_before = defaultdict(float)
        anchor_delivery = receipt.inter_wh_delivery_id
        if anchor_delivery:
            done_receipts = (
                self.env["stock.picking"]
                .sudo()
                .search(
                    [
                        ("picking_type_code", "=", "incoming"),
                        ("inter_wh_delivery_id", "=", anchor_delivery.id),
                        ("state", "=", "done"),
                    ]
                )
            )
            for move in done_receipts.move_ids:
                if move.state == "done":
                    received_before[move.product_id] += move.quantity
        for product, rqty in received_before.items():
            delivered_qty[product] -= rqty

        changes = []  # (mahsulot nomi, so'ralgan, yuborilgan)

        def _prepare_line_vals(product):
            """Delivery move line'laridan (lotlar bilan) receipt line'lar tayyorlash"""
            # Bir qismi avval qabul qilingan bo'lsa, lotlarni qo'lda ko'chirmaymiz -
            # action_assign tranzitdagi qoldiqdan lotlarni o'zi zaxira qiladi.
            if received_before.get(product):
                return []
            vals = []
            for line in delivered_lines.get(product, []):
                line_qty = (
                    line.quantity if hasattr(line, "quantity") else line.qty_done
                )
                if line_qty <= 0:
                    continue
                vals.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_uom_id": line.product_uom_id.id,
                            "lot_id": line.lot_id.id,
                            "quantity": line_qty,
                            "location_id": transit_location.id,
                            "location_dest_id": dest_location.id,
                        },
                    )
                )
            return vals

        # 2. Zayavkadagi mavjud qatorlarni yangilash
        for r_move in receipt.move_ids:
            if r_move.state in ("done", "cancel"):
                continue
            product = r_move.product_id
            requested = r_move.product_uom_qty
            sent = delivered_qty.pop(product, 0.0)
            rounding = r_move.product_uom.rounding or 0.001

            if float_compare(sent, requested, precision_rounding=rounding) != 0:
                changes.append((product.display_name, requested, sent))

            if float_compare(sent, 0.0, precision_rounding=rounding) <= 0:
                # Bu mahsulot umuman yuborilmagan - qatorni bekor qilamiz
                r_move._action_cancel()
                continue

            # Miqdorni haqiqiy yuborilganga tenglashtiramiz
            r_move.product_uom_qty = sent

            # Lot/serial ma'lumotlarini ko'chirish
            line_vals = _prepare_line_vals(product)
            if line_vals:
                r_move.move_line_ids.unlink()
                r_move.write({"move_line_ids": line_vals})

        # 3. Zayavkada yo'q, lekin yuborilgan mahsulotlar uchun yangi qatorlar
        for product, sent in delivered_qty.items():
            if sent <= 0:
                continue
            changes.append((product.display_name, 0.0, sent))
            receipt.write(
                {
                    "move_ids": [
                        (
                            0,
                            0,
                            {
                                "description_picking": product.display_name,
                                "product_id": product.id,
                                "product_uom_qty": sent,
                                "product_uom": product.uom_id.id,
                                "location_id": transit_location.id,
                                "location_dest_id": dest_location.id,
                                "move_line_ids": _prepare_line_vals(product),
                            },
                        )
                    ]
                }
            )

        # Yangi qo'shilgan qatorlarni confirm/assign qilish
        receipt.action_confirm()
        receipt.action_assign()

        # 4. Farq bo'lsa - qabul qiluvchi omborga bildirishnoma
        if changes:
            lines_txt = "".join(
                _("<li><b>%s</b> — so'ralgan: %s, yuborilgan: %s</li>")
                % (name, requested, sent)
                for name, requested, sent in changes
            )
            message_body = _(
                "Diqqat! <b>%s</b> delivery bo'yicha yuborilgan miqdorlar "
                "zayavkadagidan farq qiladi:<ul>%s</ul>"
                "Zayavka miqdorlari haqiqiy yuborilgan miqdorga moslab yangilandi."
            ) % (self.name, lines_txt)
            receipt._send_notification_to_users(
                receipt.picking_type_id.warehouse_id, message_body
            )

    def _check_over_receipt(self, delivery):
        """
        Zayavka (Receipt) validate qilinayotganda, yuborilganidan ko'p
        qabul qilishni taqiqlash. Aks holda tranzit lokatsiya minusga
        tushib, qabul qiluvchi omborda yo'q mahsulot 'paydo bo'ladi'.
        """
        self.ensure_one()
        delivery = delivery.sudo()

        # Butun delivery zanjiri (asosiy + backorderlar) bo'yicha yuborilganlar
        delivery_domain = [
            ("picking_type_code", "=", "outgoing"),
            ("state", "=", "done"),
            ("destination_warehouse_id", "!=", False),
        ]
        if delivery.origin:
            delivery_domain.append(("origin", "=", delivery.origin))
        else:
            delivery_domain.append(("id", "=", delivery.id))
        deliveries = self.env["stock.picking"].sudo().search(delivery_domain)

        delivered = defaultdict(float)
        for move in deliveries.move_ids:
            if move.state == "done":
                delivered[move.product_id.id] += move.quantity

        # Shu zanjir bo'yicha avval qabul qilib bo'linganlarni ayiramiz
        done_receipts = (
            self.env["stock.picking"]
            .sudo()
            .search(
                [
                    ("picking_type_code", "=", "incoming"),
                    ("inter_wh_delivery_id", "=", delivery.id),
                    ("state", "=", "done"),
                    ("id", "!=", self.id),
                ]
            )
        )
        for move in done_receipts.move_ids:
            if move.state == "done":
                delivered[move.product_id.id] -= move.quantity

        to_receive = defaultdict(float)
        for move in self.move_ids:
            if move.state in ("done", "cancel"):
                continue
            qty = move.quantity if hasattr(move, "quantity") else move.quantity_done
            to_receive[move.product_id.id] += qty

        for product_id, qty in to_receive.items():
            sent = delivered.get(product_id, 0.0)
            if float_compare(qty, sent, precision_digits=3) > 0:
                product = self.env["product.product"].sudo().browse(product_id)
                raise ValidationError(
                    _(
                        "'%s' mahsulotidan yuborilganidan ko'p qabul qilib bo'lmaydi!\n"
                        "Yuborilgan: %s, qabul qilinmoqchi: %s"
                    )
                    % (product.display_name, sent, qty)
                )

    def _create_backorder(self, *args, **kwargs):
        """
        Backorder yaratilganda inter-warehouse maydonlarini nusxalash.
        Bu maydonlar copy=False bo'lgani uchun standart nusxalashda yo'qoladi,
        natijada backorder yuk tranzitda 'egasiz' qolib ketardi.
        """
        backorders = super(StockPicking, self)._create_backorder(*args, **kwargs)
        for backorder in backorders:
            origin_picking = backorder.backorder_id
            if not origin_picking:
                continue
            vals = {}
            if origin_picking.sudo().destination_warehouse_id:
                vals["destination_warehouse_id"] = (
                    origin_picking.sudo().destination_warehouse_id.id
                )
            if origin_picking.sudo().source_warehouse_id:
                vals["source_warehouse_id"] = (
                    origin_picking.sudo().source_warehouse_id.id
                )
            if origin_picking.sudo().inter_wh_delivery_id:
                vals["inter_wh_delivery_id"] = (
                    origin_picking.sudo().inter_wh_delivery_id.id
                )
            if vals:
                backorder.sudo().write(vals)
        return backorders

    def _send_notification_to_users(self, warehouse, message_body):
        """ Omborga mas'ul foydalanuvchilarga xabar yuborish (Sudo bilan) """
        warehouse_sudo = warehouse.sudo()
        try:
            recipient_users = warehouse_sudo.allowed_user_ids #
            if recipient_users:
                recipient_partners = recipient_users.mapped('partner_id').ids

                # Xabarni Chatter-ga tizim bildirishnomasi sifatida yozish
                self.sudo().message_post(
                    body=message_body,
                    subject=_("Yuk yuborildi: %s") % self.name,
                    partner_ids=recipient_partners,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
        except Exception as e:
            _logger.error("Notification yuborishda xato: %s", str(e))

    # ------------------------------------------------------------------ #
    #  Onchange helpers                                                    #
    # ------------------------------------------------------------------ #

    @api.onchange("destination_warehouse_id")
    def _onchange_destination_warehouse(self):
        """Ombor tanlanganda manzilni Tranzitga o'zgartirish"""
        if self.destination_warehouse_id:
            transit_loc = (
                self.env["stock.location"]
                .sudo()
                .search(
                    [
                        ("name", "=", "Inter Warehouse Transfer"),
                        ("usage", "=", "internal"),
                    ],
                    limit=1,
                )
            )
            if transit_loc:
                self.location_dest_id = transit_loc.id
                for move in self.move_ids:
                    move.location_dest_id = transit_loc.id

    @api.onchange("source_warehouse_id")
    def _onchange_source_warehouse(self):
        """Yuboruvchi ombor tanlanganda Receipt manbasini Tranzitga o'zgartirish"""
        if self.source_warehouse_id:
            transit_loc = (
                self.env["stock.location"]
                .sudo()
                .search(
                    [
                        ("name", "=", "Inter Warehouse Transfer"),
                        ("usage", "=", "internal"),
                    ],
                    limit=1,
                )
            )
            if transit_loc:
                self.location_id = transit_loc.id
                for move in self.move_ids:
                    move.location_id = transit_loc.id
        else:
            if self.picking_type_id:
                self.location_id = self.picking_type_id.default_location_src_id.id
