# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    inter_wh_delivery_id = fields.Many2one(
        "stock.picking", string="Bog'liq Delivery", copy=False
    )

    def action_confirm(self):
        """Mark as Todo bosilganda ishlaydi"""
        res = super(StockPicking, self).action_confirm()

        for picking in self:
            # Agar bu Kirim bo'lsa va Yuboruvchi ombor tanlangan bo'lsa -> Delivery yaratish
            if picking.picking_type_code == "incoming" and picking.source_warehouse_id:
                picking._create_delivery_from_zayavka()

        return res

    def _create_delivery_from_zayavka(self):
        """Manba ombor uchun Delivery yaratish va uni Ready holatiga o'tkazish"""
        self.ensure_one()

        transit_location = self.env["stock.location"].search(
            [("name", "=", "Inter Warehouse Transfer"), ("usage", "=", "internal")],
            limit=1,
        )

        source_picking_type = self.env["stock.picking.type"].search(
            [
                ("warehouse_id", "=", self.source_warehouse_id.id),
                ("code", "=", "outgoing"),
            ],
            limit=1
        )

        if not source_picking_type:
            raise ValidationError(
                _("%s ombori uchun 'Delivery' turi topilmadi.")
                % self.source_warehouse_id.name
            )

        delivery_vals = {
            "picking_type_id": source_picking_type.id,
            "location_id": source_picking_type.default_location_src_id.id,
            "location_dest_id": transit_location.id,
            "origin": self.name,  # Zayavka raqami (masalan: IN/0001)
            "destination_warehouse_id": self.warehouse_id.id,
            "move_ids_without_package": [
                (
                    0,
                    0,
                    {
                        "name": move.name,
                        "product_id": move.product_id.id,
                        "product_uom_qty": move.product_uom_qty,
                        "product_uom": move.product_uom.id,
                        "location_id": source_picking_type.default_location_src_id.id,
                        "location_dest_id": transit_location.id,
                    },
                )
                for move in self.move_ids_without_package
            ],
        }

        delivery = self.env["stock.picking"].create(delivery_vals)
        self.inter_wh_delivery_id = delivery

        # Delivery'ni darhol tasdiqlash (Mark as Todo) va zaxira qilish (Check Availability)
        delivery.action_confirm()
        delivery.action_assign()  # Agar mahsulot bo'lsa, 'Ready' holatiga o'tadi

    def button_validate(self):
        """Validatsiya mantiqlari"""
        for picking in self:
            # 1. Manzilni tranzitga yo'naltirish (Customer'ga ketib qolmasligi uchun)
            if (
                picking.destination_warehouse_id
                and picking.picking_type_code == "outgoing"
            ):
                transit_loc = self.env["stock.location"].search(
                    [
                        ("name", "=", "Inter Warehouse Transfer"),
                        ("usage", "=", "internal"),
                    ],
                    limit=1,
                )
                if transit_loc:
                    picking.location_dest_id = transit_loc.id
                    for move in picking.move_ids_without_package:
                        move.location_dest_id = transit_loc.id

            # 2. Zayavka (Receipt) ni tekshirish
            if picking.picking_type_code == "incoming" and picking.inter_wh_delivery_id:
                if picking.inter_wh_delivery_id.state != "done":
                    raise ValidationError(
                        _(
                            "Ushbu zayavkani qabul qila olmaysiz! "
                            "Avval yuboruvchi ombor yukni jo'natishi kerak."
                        )
                    )

        # Standart validatsiyani chaqiramiz
        res = super(StockPicking, self).button_validate()

        for picking in self:
            # 3. Delivery tasdiqlanganda avtomatik Receipt yaratish
            if (
                picking.state == "done"
                and picking.picking_type_code == "outgoing"
                and picking.destination_warehouse_id
            ):
                # Eng muhim joyi: Haqiqatda bizga tegishli Receipt bormi yoki yo'qligini tekshirish
                # Faqatgina ushbu Delivery'ga aynan bog'langan (Source Document) Receipt bo'lsa yaratmaydi
                is_zayavka_based = False
                if picking.origin:
                    existing_receipt = self.env["stock.picking"].search(
                        [
                            ("name", "=", picking.origin),
                            ("picking_type_code", "=", "incoming"),
                            (
                                "source_warehouse_id",
                                "!=",
                                False,
                            ),  # Bu bizning zayavka ekanligini bildiradi
                        ],
                        limit=1,
                    )
                    if existing_receipt:
                        is_zayavka_based = True

                # Agar bu zayavka asosida bo'lmasa, yangi Receipt yaratamiz
                if not is_zayavka_based:
                    self._create_inter_warehouse_receipt(picking)

        return res

    # 2. Validatsiya: O'z omboriga o'zi yubora olmasligi kerak
    @api.constrains("destination_warehouse_id", "picking_type_id")
    def _check_destination_warehouse(self):
        for picking in self:
            if (
                picking.destination_warehouse_id
                and picking.picking_type_id.warehouse_id
                == picking.destination_warehouse_id
            ):
                raise ValidationError(
                    _("Mahsulotni ayni shu omborning o'ziga yubora olmaysiz!")
                )

    def _create_inter_warehouse_receipt(self, picking):
        """Qabul qiluvchi ombor uchun avtomatik Receipt yaratish (Lotlar bilan)"""

        if picking.origin and self.env["stock.picking"].search(
            [("name", "=", picking.origin), ("picking_type_code", "=", "incoming")]
        ):
            return

        transit_location = self.env["stock.location"].search(
            [("name", "=", "Inter Warehouse Transfer"), ("usage", "=", "internal")],
            limit=1,
        )

        dest_picking_type = self.env["stock.picking.type"].search(
            [
                ("warehouse_id", "=", picking.destination_warehouse_id.id),
                ("code", "=", "incoming"),
            ],
            limit=1,
        )

        receipt_vals = {
            "picking_type_id": dest_picking_type.id,
            "location_id": transit_location.id,
            "location_dest_id": dest_picking_type.default_location_dest_id.id,
            "origin": picking.name,
            "move_ids_without_package": [],
        }

        for move in picking.move_ids_without_package:
            qty = move.quantity
            if qty <= 0:
                qty = move.product_uom_qty

            # Move line (Lotlar) ma'lumotlarini tayyorlaymiz
            move_line_vals = []
            for line in move.move_line_ids:
                move_line_vals.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_uom_id": line.product_uom_id.id,
                            "lot_id": line.lot_id.id,  # Asosiy qism: Lot raqamini ko'chirish
                            "quantity": line.quantity
                            if hasattr(line, "quantity")
                            else line.qty_done,
                            "location_id": transit_location.id,
                            "location_dest_id": dest_picking_type.default_location_dest_id.id,
                        },
                    )
                )

            receipt_vals["move_ids_without_package"].append(
                (
                    0,
                    0,
                    {
                        "name": move.name,
                        "product_id": move.product_id.id,
                        "product_uom_qty": qty,
                        "product_uom": move.product_uom.id,
                        "location_id": transit_location.id,
                        "location_dest_id": dest_picking_type.default_location_dest_id.id,
                        "move_line_ids": move_line_vals,  # Lotlarni bog'lash
                    },
                )
            )

        if receipt_vals["move_ids_without_package"]:
            new_receipt = self.env["stock.picking"].create(receipt_vals)
            new_receipt.action_confirm()
            # Agar lotlar kiritilgan bo'lsa, darhol 'Assigned' holatiga o'tkazishga harakat qilamiz
            new_receipt.action_assign()

    @api.onchange("destination_warehouse_id")
    def _onchange_destination_warehouse(self):
        """Ombor tanlanganda manzilni Tranzitga o'zgartirish"""
        if self.destination_warehouse_id:
            transit_loc = self.env["stock.location"].search(
                [("name", "=", "Inter Warehouse Transfer"), ("usage", "=", "internal")],
                limit=1,
            )

            if transit_loc:
                self.location_dest_id = transit_loc.id
                # Mahsulot qatorlarining manzillarini ham yangilash
                for move in self.move_ids_without_package:
                    move.location_dest_id = transit_loc.id

    @api.onchange("source_warehouse_id")
    def _onchange_source_warehouse(self):
        """Yuboruvchi ombor tanlanganda Receipt manbasini Tranzitga o'zgartirish"""
        if self.source_warehouse_id:
            transit_loc = self.env["stock.location"].search(
                [("name", "=", "Inter Warehouse Transfer"), ("usage", "=", "internal")],
                limit=1,
            )

            if transit_loc:
                self.location_id = transit_loc.id
                # Mahsulot qatorlarining manba lokatsiyasini ham tranzitga o'zgartiramiz
                for move in self.move_ids_without_package:
                    move.location_id = transit_loc.id
        else:
            # Agar tanlov olib tashlansa, standart Vendor lokatsiyasiga qaytarish
            if self.picking_type_id:
                self.location_id = self.picking_type_id.default_location_src_id.id


# # -*- coding: utf-8 -*-
# import logging
# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError
#
# _logger = logging.getLogger(__name__)
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     warehouse_id = fields.Many2one(
#         related='picking_type_id.warehouse_id',
#         string="Ombor",
#         readonly=True,
#         store=True
#     )
#
#     source_warehouse_id = fields.Many2one(
#         'custom.warehouse',
#         string="Yuboruvchi ombor",
#         copy=False,
#         domain="[('company_id', '=', company_id), ('real_warehouse_id', '!=', warehouse_id)]"
#     )
#
#     destination_warehouse_id = fields.Many2one(
#         'custom.warehouse',
#         string="Qabul qiluvchi ombor",
#         # Mana shu domain begona kompaniyalarni yo'qotadi:
#         domain="[('company_id', '=', company_id), ('real_warehouse_id', '!=', warehouse_id)]"
#     )
#
#     inter_wh_delivery_id = fields.Many2one('stock.picking', string="Bog'liq Delivery", copy=False)
#
#     def _get_transit_location(self):
#         """ Tranzit lokatsiyasini joriy kompaniyaga mos holda qidirish """
#         self.ensure_one()
#         transit_loc = self.env['stock.location'].sudo().search([
#             ('name', '=', 'Inter Warehouse Transfer'),
#             ('usage', '=', 'internal'),
#             ('company_id', '=', self.company_id.id) # Kompaniyaga qat'iy bog'laymiz
#         ], limit=1)
#
#         if not transit_loc:
#             # Agar bu kompaniyada hali yo'q bo'lsa, kompaniyasiz (umumiy) lokatsiyani qidiramiz
#             transit_loc = self.env['stock.location'].sudo().search([
#                 ('name', '=', 'Inter Warehouse Transfer'),
#                 ('usage', '=', 'internal'),
#                 ('company_id', '=', False)
#             ], limit=1)
#
#         if not transit_loc:
#             raise ValidationError(_("Xatolik: '%s' kompaniyasi uchun tranzit lokatsiyasi topilmadi!") % self.company_id.name)
#         return transit_loc
#
#     def action_confirm(self):
#         """ Mark as Todo bosilganda ishlaydi """
#         res = super(StockPicking, self).action_confirm()
#         for picking in self:
#             # MUHIM: Faqat ZAYAVKA bo'lsa (ya'ni qo'lda source_warehouse_id tanlangan bo'lsa) Delivery yaratadi
#             # Agar bu avtomatik yaratilgan Receipt bo'lsa (origin bor bo'lsa), Delivery yaratmaydi
#             if picking.picking_type_code == 'incoming' and picking.source_warehouse_id and not picking.origin:
#                 picking._create_delivery_from_zayavka()
#         return res
#
#     def _create_delivery_from_zayavka(self):
#         self.ensure_one()
#         # sudo() orqali lokatsiyani qidiramiz
#         transit_location = self.sudo()._get_transit_location()
#         real_source_wh = self.source_warehouse_id.real_warehouse_id
#
#         # sudo() orqali picking type qidiramiz
#         source_picking_type = self.env['stock.picking.type'].sudo().search([
#             ('warehouse_id', '=', real_source_wh.id),
#             ('code', '=', 'outgoing'),
#             ('company_id', '=', real_source_wh.company_id.id)
#         ], limit=1)
#
#         if not source_picking_type:
#             raise ValidationError(_("%s ombori uchun 'Delivery' turi topilmadi.") % self.source_warehouse_id.name)
#
#         current_custom_wh = self.env['custom.warehouse'].sudo().search([
#             ('real_warehouse_id', '=', self.warehouse_id.id)
#         ], limit=1)
#
#         delivery_vals = {
#             'picking_type_id': source_picking_type.id,
#             'company_id': source_picking_type.company_id.id,
#             'location_id': source_picking_type.default_location_src_id.id,
#             'location_dest_id': transit_location.id,
#             'origin': self.name,
#             'destination_warehouse_id': current_custom_wh.id,
#             'move_ids_without_package': [(0, 0, {
#                 'name': move.name,
#                 'product_id': move.product_id.id,
#                 'product_uom_qty': move.product_uom_qty,
#                 'product_uom': move.product_uom.id,
#                 'location_id': source_picking_type.default_location_src_id.id,
#                 'location_dest_id': transit_location.id,
#                 'company_id': source_picking_type.company_id.id,
#             }) for move in self.move_ids_without_package],
#         }
#
#         # Hujjat yaratish, tasdiqlash va zaxira qilish hammasi sudo() orqali
#         delivery = self.env['stock.picking'].sudo().create(delivery_vals)
#         self.sudo().write({'inter_wh_delivery_id': delivery.id})
#         delivery.sudo().action_confirm()
#         delivery.sudo().action_assign()
#
#     def button_validate(self):
#         """ Validatsiya mantiqlari """
#         for picking in self:
#             # 1. Tranzit lokatsiyaga yo'naltirish (sudo bilan)
#             if picking.destination_warehouse_id and picking.picking_type_code == 'outgoing':
#                 transit_loc = picking.sudo()._get_transit_location()
#                 picking.sudo().write({'location_dest_id': transit_loc.id})
#                 for move in picking.move_ids_without_package:
#                     move.sudo().write({'location_dest_id': transit_loc.id})
#
#             # 2. Zayavkani tekshirish
#             if picking.picking_type_code == 'incoming' and picking.inter_wh_delivery_id:
#                 if picking.inter_wh_delivery_id.sudo().state != 'done':
#                     raise ValidationError(_("Avval yuboruvchi ombor yukni jo'natishi (Validate) kerak."))
#
#         # Standart validatsiyani chaqiramiz
#         res = super(StockPicking, self).button_validate()
#
#         for picking in self:
#             if picking.state == 'done' and picking.picking_type_code == 'outgoing' and picking.destination_warehouse_id:
#                 is_from_zayavka = False
#                 if picking.origin:
#                     source_receipt = self.env['stock.picking'].sudo().search([
#                         ('name', '=', picking.origin),
#                         ('picking_type_code', '=', 'incoming')
#                     ], limit=1)
#                     if source_receipt:
#                         is_from_zayavka = True
#
#                 if not is_from_zayavka:
#                     # Receipt yaratishni sudo orqali chaqiramiz
#                     picking.sudo()._create_inter_warehouse_receipt(picking)
#         return res
#
#     def _create_inter_warehouse_receipt(self, picking):
#         """ Qabul qiluvchi ombor uchun avtomatik Receipt yaratish """
#         transit_location = self.sudo()._get_transit_location()
#         real_dest_wh = picking.destination_warehouse_id.real_warehouse_id
#
#         dest_picking_type = self.env['stock.picking.type'].sudo().search([
#             ('warehouse_id', '=', real_dest_wh.id),
#             ('code', '=', 'incoming'),
#             ('company_id', '=', real_dest_wh.company_id.id)
#         ], limit=1)
#
#         if not dest_picking_type:
#             return
#
#         receipt_vals = {
#             'picking_type_id': dest_picking_type.id,
#             'company_id': dest_picking_type.company_id.id,
#             'location_id': transit_location.id,
#             'location_dest_id': dest_picking_type.default_location_dest_id.id,
#             'origin': picking.name,
#             'source_warehouse_id': False,
#             'move_ids_without_package': [],
#         }
#
#         for move in picking.move_ids_without_package:
#             qty = move.quantity if hasattr(move, 'quantity') else move.product_uom_qty
#
#             move_line_vals = []
#             for line in move.move_line_ids:
#                 move_line_vals.append((0, 0, {
#                     'product_id': line.product_id.id,
#                     'lot_id': line.lot_id.id,
#                     'quantity': line.quantity if hasattr(line, 'quantity') else line.qty_done,
#                     'location_id': transit_location.id,
#                     'location_dest_id': dest_picking_type.default_location_dest_id.id,
#                     'company_id': dest_picking_type.company_id.id,
#                 }))
#
#             receipt_vals['move_ids_without_package'].append((0, 0, {
#                 'name': move.name,
#                 'product_id': move.product_id.id,
#                 'product_uom_qty': qty,
#                 'product_uom': move.product_uom.id,
#                 'location_id': transit_location.id,
#                 'location_dest_id': dest_picking_type.default_location_dest_id.id,
#                 'move_line_ids': move_line_vals,
#                 'company_id': dest_picking_type.company_id.id,
#             }))
#
#         if receipt_vals['move_ids_without_package']:
#             # Create, confirm va assign amallarini sudo bilan bajaramiz
#             new_receipt = self.env['stock.picking'].sudo().create(receipt_vals)
#             new_receipt.sudo().action_confirm()
#             new_receipt.sudo().action_assign()
#
#     @api.onchange('destination_warehouse_id', 'source_warehouse_id')
#     def _onchange_transit_locations(self):
#         transit_loc = self.env['stock.location'].sudo().search([('name', '=', 'Inter Warehouse Transfer')], limit=1)
#         if not transit_loc: return
#         for picking in self:
#             if picking.destination_warehouse_id and picking.picking_type_code == 'outgoing':
#                 picking.location_dest_id = transit_loc.id
#             if picking.source_warehouse_id and picking.picking_type_code == 'incoming':
#                 picking.location_id = transit_loc.id
#
# class CustomWarehouse(models.Model):
#     _name = 'custom.warehouse'
#     _description = 'Custom Warehouse List'
#
#     name = fields.Char(string="Ombor nomi", required=True)
#     real_warehouse_id = fields.Many2one('stock.warehouse', string="Asl Ombor", required=True)
#     # Yangi maydon:
#     company_id = fields.Many2one('res.company', string="Kompaniya",
#                                  related='real_warehouse_id.company_id', store=True)
#
# class StockWarehouse(models.Model):
#     _inherit = 'stock.warehouse'
#
#     def force_reinit_custom_warehouses(self):
#         # Har doim admin huquqi bilan ishlash
#         CustomWH = self.env['custom.warehouse'].sudo()
#
#         # 1. FAQAT joriy kompaniyaga tegishli eski yozuvlarni tozalash
#         current_company_id = self.env.company.id
#         CustomWH.search([('company_id', '=', current_company_id)]).unlink()
#
#         # 2. Real omborlarni qidirish (Sudo hamma omborni ko'rishni ta'minlaydi)
#         real_warehouses = self.env['stock.warehouse'].sudo().search([
#             ('company_id', '=', current_company_id)
#         ])
#
#         for wh in real_warehouses:
#             CustomWH.create({
#                 'name': wh.name,
#                 'real_warehouse_id': wh.id,
#                 'company_id': wh.company_id.id,
#             })
#         return True
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         warehouses = super(StockWarehouse, self).create(vals_list)
#         # Yangi ombor yaratilganda sinxronizatsiyani ishga tushirish
#         self._sync_all_to_custom_warehouses()
#         return warehouses
#
#     def write(self, vals):
#         res = super(StockWarehouse, self).write(vals)
#         # Nomi yoki boshqa muhim maydoni o'zgarganda yangilash
#         if 'name' in vals:
#             self._sync_all_to_custom_warehouses()
#         return res
