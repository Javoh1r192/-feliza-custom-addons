# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = "stock.move"

    # ------------------------------------------------------------------ #
    #  Hisobot uchun: harakatning HAQIQIY (tranzit lokatsiyasidan          #
    #  qat'i nazar) boshlang'ich va yakuniy ombori.                        #
    #                                                                       #
    #  Standart Odoo hisobotlarida location_id/location_dest_id har doim   #
    #  "Inter Warehouse Transfer" bo'lib ko'rinadi, chunki jismoniy         #
    #  harakat shu tranzit orqali amalga oshadi. Quyidagi ikki maydon esa   #
    #  yukning HAQIQIY qaysi ombordan qaysi omborga borayotganini          #
    #  ko'rsatadi va pivot/graph hisobotlarda ishlatish uchun mo'ljallangan.#
    # ------------------------------------------------------------------ #
    real_source_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Haqiqiy yuboruvchi ombor",
        compute="_compute_real_warehouses",
        store=True,
        help=(
            "Tranzit lokatsiyasidan (Inter Warehouse Transfer) qat'i nazar, "
            "yukning haqiqiy jo'natilgan ombori. Faqat omborlar aro "
            "o'tkazma harakatlari uchun to'ldiriladi."
        ),
    )
    real_dest_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Haqiqiy qabul qiluvchi ombor",
        compute="_compute_real_warehouses",
        store=True,
        help=(
            "Tranzit lokatsiyasidan (Inter Warehouse Transfer) qat'i nazar, "
            "yukning haqiqiy yetib borgan ombori. Faqat omborlar aro "
            "o'tkazma harakatlari uchun to'ldiriladi."
        ),
    )

    @api.depends(
        "picking_id.picking_type_code",
        "picking_id.warehouse_id",
        "picking_id.destination_warehouse_id",
        "picking_id.source_warehouse_id",
        "picking_id.inter_wh_delivery_id",
        "picking_id.inter_wh_delivery_id.warehouse_id",
    )
    def _compute_real_warehouses(self):
        for move in self:
            picking = move.picking_id.sudo()
            src_wh = dest_wh = False

            if picking.picking_type_code == "outgoing" and picking.destination_warehouse_id:
                # Omborlar aro Delivery: haqiqiy jo'natuvchi - picking'ning
                # o'z ombori, haqiqiy qabul qiluvchi - destination_warehouse_id.
                src_wh = picking.warehouse_id
                dest_wh = picking.destination_warehouse_id

            elif picking.picking_type_code == "incoming":
                # Omborlar aro Receipt - ikkita ko'rinishda bo'lishi mumkin:
                #  1) Pull/zayavka oqimi: source_warehouse_id to'g'ridan-to'g'ri
                #     foydalanuvchi tomonidan tanlangan.
                #  2) Push oqimi: avtomatik yaratilgan, source_warehouse_id
                #     bo'sh, lekin inter_wh_delivery_id orqali Delivery'ga
                #     bog'langan - o'sha Delivery'ning ombori haqiqiy manba.
                if picking.source_warehouse_id:
                    src_wh = picking.source_warehouse_id
                elif picking.inter_wh_delivery_id:
                    src_wh = picking.inter_wh_delivery_id.sudo().warehouse_id

                if src_wh:
                    dest_wh = picking.warehouse_id

            move.real_source_warehouse_id = src_wh
            move.real_dest_warehouse_id = dest_wh

    # ------------------------------------------------------------------ #
    #  Hisobotda BITTA transfer BITTA marta, va HAR DOIM YAKUNIY HAQIQIY   #
    #  holat bilan ko'rinishi uchun.                                       #
    #                                                                       #
    #  Har bir omborlar aro o'tkazma bir necha jismoniy harakatdan iborat   #
    #  bo'lishi mumkin:                                                     #
    #    1) Delivery (A -> Tranzit)                                        #
    #    2) Receipt (Tranzit -> B) - to'liq yoki qisman                    #
    #    3) Agar B "No Backorder" bilan kam qabul qilsa va A qolganini      #
    #       "Return" qilib qaytarib olsa - Return (Tranzit -> A)           #
    #                                                                       #
    #  Return harakatlari ATAYLAB hisobotda alohida qator sifatida         #
    #  ko'rsatilmaydi (murakkab "ombor -> o'zi" ko'rinishiga olib kelardi). #
    #  Lekin ularning miqdori baribir hisobga olinadi: Delivery'ning        #
    #  "Yo'lda" qoldig'i - qabul qilingan VA qaytarilgan miqdorlarning      #
    #  yig'indisi ayrilgandan keyingi qoldiq. Ya'ni:                        #
    #      yo'lda (ko'rinadigan) + yetib bordi (ko'rinadigan)               #
    #      + qaytarilgan (ko'rinmaydigan, lekin hisobga olingan)            #
    #      = yuborilgan                                                    #
    #                                                                       #
    #  Bu maydonlar hisoblangan (backfill uchun), lekin amalda              #
    #  button_validate ichida to'g'ridan-to'g'ri yozib ham qo'yiladi        #
    #  (stock_picking.py) - chunki turli picking'lar orasidagi bog'liqlik   #
    #  o'zgarishini avtomatik (depends orqali) kuzatishning ishonchli       #
    #  yo'li yo'q.                                                          #
    # ------------------------------------------------------------------ #
    interwh_report_status = fields.Selection(
        [
            ("in_transit", "Yo'lda"),
            ("arrived", "Yetib bordi"),
        ],
        string="Omborlar aro hisobot holati",
        compute="_compute_interwh_report_status",
        store=True,
        help=(
            "Omborlar aro tarqatish hisobotida ushbu harakat ko'rsatilishi "
            "kerakmi va qanday holatda ko'rsatilishi kerakligini belgilaydi. "
            "Bo'sh bo'lsa - hisobotda ko'rinmaydi. Eslatma: 'Return' "
            "(qaytarish) harakatlari ataylab hisobotda alohida qator "
            "sifatida ko'rsatilmaydi - ular faqat bog'liq Delivery'ning "
            "'Yo'lda' qoldig'ini kamaytirish uchun fonda hisobga olinadi "
            "(_interwh_resolved_qty orqali)."
        ),
    )
    interwh_report_qty = fields.Float(
        string="Hisobot miqdori",
        compute="_compute_interwh_report_status",
        store=True,
        digits="Product Unit of Measure",
        help=(
            "Hisobotda ko'rsatiladigan miqdor. 'Yetib bordi' uchun - "
            "haqiqiy qabul qilingan miqdor. 'Yo'lda' uchun - hali hal "
            "qilinMAGAN qoldiq miqdor (qabul qilingan VA qaytarilgan "
            "miqdorlar ayrilgandan keyin)."
        ),
    )

    def _interwh_resolved_qty(self, delivery, product):
        """Berilgan Delivery va mahsulot bo'yicha, hozirgacha HAL QILINGAN
        (B tomonidan qabul qilingan + A ga qaytarilgan) umumiy miqdorni
        hisoblaydi. Delivery'dagi qoldiq ('yo'lda') shundan kelib chiqadi:
        qoldiq = yuborilgan - hal_qilingan.
        """
        delivery_moves = delivery.sudo().move_ids.filtered(
            lambda m, p=product: m.product_id == p
        )
        received_moves = self.env["stock.move"].sudo().search(
            [
                ("picking_id.inter_wh_delivery_id", "=", delivery.id),
                ("product_id", "=", product.id),
                ("state", "=", "done"),
            ]
        )
        returned_moves = self.env["stock.move"].sudo().search(
            [
                ("origin_returned_move_id", "in", delivery_moves.ids),
                ("state", "=", "done"),
            ]
        )
        return sum(received_moves.mapped("quantity")) + sum(returned_moves.mapped("quantity"))

    @api.depends(
        "state",
        "quantity",
        "product_id",
        "picking_id.picking_type_code",
        "picking_id.state",
        "picking_id.destination_warehouse_id",
        "picking_id.inter_wh_delivery_id",
    )
    def _compute_interwh_report_status(self):
        for move in self:
            picking = move.picking_id.sudo()
            status = False
            qty = 0.0

            if move.state == "done" and picking.picking_type_code == "outgoing" and picking.destination_warehouse_id:
                resolved = move._interwh_resolved_qty(picking, move.product_id)
                rounding = move.product_uom.rounding or 0.001
                outstanding = move.quantity - resolved
                # TUZATISH: avval `outstanding > rounding` edi. "Product Unit"
                # aniqligi 0 ga qo'yilgan bazada rounding = 1.0 bo'ladi, shuning
                # uchun ROSA 1 DONA qoldiq (1.0 > 1.0 -> False) hisobotdan
                # tushib qolardi. To'g'ri savol — "qoldiq noldan katta-mi",
                # ya'ni nolga nisbatan yaxlitlash bilan solishtirish.
                if float_compare(outstanding, 0.0, precision_rounding=rounding) > 0:
                    status = "in_transit"
                    qty = outstanding
                else:
                    status = False
                    qty = 0.0

            elif move.state == "done" and picking.picking_type_code == "incoming" and picking.inter_wh_delivery_id:
                status = "arrived"
                qty = move.quantity

            # Eslatma: "Return" (qaytarish) harakatlari uchun ataylab
            # status/qty belgilanmaydi (False/0.0 bo'lib qoladi) - ular
            # hisobotda alohida qator sifatida ko'rinmaydi. Ularning
            # miqdori baribir _interwh_resolved_qty() orqali bog'liq
            # Delivery'ning "Yo'lda" qoldig'ini to'g'ri kamaytiradi.

            move.interwh_report_status = status
            move.interwh_report_qty = qty

    # ------------------------------------------------------------------ #
    #  Ro'yxat ko'rinishida "Qabul qiluvchi ombor" ustuni uchun.            #
    #  "Qaytarildi" holatida shu ombor nomini takrorlash ("Main Sklad"     #
    #  ikki marta) chalkash ko'rinadi - buning o'rniga aniq matn           #
    #  ko'rsatiladi. Pivot/Graph hisobotlarda esa (guruhlash uchun)        #
    #  haqiqiy real_dest_warehouse_id (Many2one) ishlatiladi - u yerda     #
    #  bu masala aktual emas.                                              #
    # ------------------------------------------------------------------ #
    interwh_report_dest_display = fields.Char(
        string="Qabul qiluvchi ombor (matn)",
        compute="_compute_interwh_report_dest_display",
        store=True,
        help="Ro'yxat ko'rinishi uchun qulay matn ko'rinishi.",
    )

    @api.depends("real_dest_warehouse_id")
    def _compute_interwh_report_dest_display(self):
        for move in self:
            move.interwh_report_dest_display = move.real_dest_warehouse_id.name or False

    # ------------------------------------------------------------------ #
    #  Tannarx (cost) ustunlari - TARIXIY (muzlatilgan).                   #
    #                                                                       #
    #  ESLATMA: Odoo 19'da stock.valuation.layer modeli butunlay olib      #
    #  tashlangan (versiyaga xos o'zgarish) - baholash endi faqat          #
    #  xarid/sotuv fakturasi tasdiqlanganda hisoblanadi, ICHKI omborlar    #
    #  aro o'tkazmalar esa moliyaviy yozuv yaratmaydi. Shuning uchun bu    #
    #  yerda "shu harakat vaqtidagi tarixiy tannarx"ni ishonchli olish     #
    #  imkoni yo'q - o'rniga mahsulotning tannarxini (product.standard_    #
    #  price) ANIQ SHU HARAKAT hisobotga qo'shilgan/yangilangan PAYTDA     #
    #  "suratga olamiz" (snapshot).                                        #
    #                                                                       #
    #  MUHIM: quyidagi @api.depends ATAYLAB "product_id.standard_price"ni  #
    #  o'z ichiga OLMAYDI. Aks holda, mahsulot narxi keyinchalik            #
    #  o'zgarganda, Odoo BARCHA eski (hatto yillar oldingi) transfer        #
    #  yozuvlarini ham avtomatik qayta hisoblab, ularning tannarxini        #
    #  "bugungi" narxga almashtirib qo'yardi - bu esa tarixiy hisobotni     #
    #  buzardi. Shu sababli narx faqat interwh_report_qty haqiqatan ham     #
    #  o'zgarganda (ya'ni yangi transfer voqeasi sodir bo'lganda) qayta     #
    #  "suratga olinadi", boshqa hech qachon emas.                         #
    # ------------------------------------------------------------------ #
    interwh_report_unit_cost = fields.Float(
        string="Tannarx (dona)",
        compute="_compute_interwh_report_cost",
        store=True,
        digits="Product Price",
        help=(
            "Ushbu transfer voqeasi sodir bo'lgan (yoki hisobotga so'nggi "
            "marta yangilangan) paytdagi mahsulot tannarxi - keyinchalik "
            "mahsulot narxi o'zgarsa ham bu qiymat o'zgarmaydi (muzlatilgan)."
        ),
    )
    interwh_report_total_cost = fields.Float(
        string="Tannarx (jami)",
        compute="_compute_interwh_report_cost",
        store=True,
        digits="Product Price",
    )

    @api.depends("interwh_report_qty")
    def _compute_interwh_report_cost(self):
        for move in self:
            unit_cost = move.product_id.standard_price
            move.interwh_report_unit_cost = unit_cost
            move.interwh_report_total_cost = unit_cost * move.interwh_report_qty
