# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class SizeDistributionWizard(models.TransientModel):
    _name = "feliza.size.distribution.wizard"
    _description = "O'lchamlarga taqsimlash sehrgari"

    picking_id = fields.Many2one(
        "stock.picking", string="Qabul", required=True, ondelete="cascade"
    )
    line_ids = fields.One2many(
        "feliza.size.distribution.wizard.line",
        "wizard_id",
        string="Rang qatorlari",
    )
    alloc_ids = fields.One2many(
        "feliza.size.distribution.wizard.alloc",
        "wizard_id",
        string="O'lcham taqsimoti",
    )

    def _populate_from_picking(self):
        """Qabuldagi mos harakatlar asosida rang qatorlarini yaratadi.

        Diqqat: bu yerda o'lcham qatorlari OLDINDAN yaratilmaydi. Kompaniyada
        "O'lcham" (is_size) atributi boshqa, aloqasiz tovar turlari
        (masalan poyabzal raqamlari, idish hajmlari) bilan birga umumiy
        ishlatilishi mumkin - shuning uchun barcha qiymatlarni oldindan
        ro'yxatga solish o'nlab keraksiz qatorga olib keladi. Buning o'rniga
        skladchi pastdagi jadvalda o'zi kerakli o'lchamni tanlab, "Qo'shish"
        orqali qator qo'shadi (nechta kerak bo'lsa, shuncha).
        """
        self.ensure_one()
        self.line_ids.unlink()
        Line = self.env["feliza.size.distribution.wizard.line"]
        for move in self.picking_id._size_split_eligible_moves():
            product = move.product_id
            Line.create(
                {
                    "wizard_id": self.id,
                    "move_id": move.id,
                    "product_id": product.id,
                    "demand_qty": move.product_uom_qty,
                }
            )

    def action_apply(self):
        """Taqsimotni qabul qatorlariga qo'llaydi."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Taqsimlanadigan qator yo'q."))
        # 0-bosqich: umumiy tekshiruvlar (manfiy miqdor, takroriy o'lcham)
        for alloc in self.alloc_ids:
            if not alloc.size_value_id:
                continue
            if alloc.quantity < 0:
                raise UserError(
                    _("'%(product)s' / '%(size)s' uchun miqdor manfiy "
                      "bo'lishi mumkin emas.",
                      product=alloc.product_id.display_name,
                      size=alloc.size_value_id.display_name)
                )
        for line in self.line_ids:
            seen_sizes = self.env["product.attribute.value"]
            for alloc in line.alloc_ids:
                if not alloc.size_value_id:
                    continue
                if alloc.size_value_id in seen_sizes:
                    raise UserError(
                        _("'%(product)s' uchun '%(size)s' o'lchami bir necha "
                          "marta kiritilgan. Har bir o'lcham uchun faqat "
                          "bitta qator bo'lishi kerak - miqdorlarni bitta "
                          "qatorga jamlang.",
                          product=line.product_id.display_name,
                          size=alloc.size_value_id.display_name)
                    )
                seen_sizes |= alloc.size_value_id
        # 1-bosqich: har bir rang uchun yig'indi talabga teng ekanini tekshiramiz
        # (kam bo'lsa ham, ortiq bo'lsa ham xato - aniq talab qilingan
        # miqdorga teng bo'lishi shart)
        #
        # DIQQAT: miqdor UMUMAN kiritilmagan qator TEKSHIRILMAYDI va
        # TEGILMAYDI. Bitta qabulda o'lchamga bo'linadigan tovar bilan
        # bo'linmaydigani (atir, sumka, bijuteriya...) aralash kelishi
        # mumkin - skladchi ularni shunchaki tashlab ketadi, hujjat
        # qatori borligicha qoladi.
        lines_to_split = self.env["feliza.size.distribution.wizard.line"]
        for line in self.line_ids:
            rounding = line.move_id.product_uom.rounding
            allocated = sum(line.alloc_ids.mapped("quantity"))
            if float_is_zero(allocated, precision_rounding=rounding):
                continue                      # bu tovar taqsimlanmaydi
            lines_to_split |= line
            if float_compare(
                allocated, line.demand_qty, precision_rounding=rounding
            ) != 0:
                if allocated > line.demand_qty:
                    hint = _("Talab qilingan miqdordan ORTIQ kiritilgan.")
                else:
                    hint = _("Talab qilingan miqdordan KAM kiritilgan.")
                raise UserError(
                    _("'%(product)s' uchun o'lchamlar bo'yicha jami miqdor "
                      "(%(alloc)s) talab qilingan miqdorga (%(demand)s) teng "
                      "bo'lishi kerak. %(hint)s",
                      product=line.product_id.display_name,
                      alloc=allocated,
                      demand=line.demand_qty,
                      hint=hint)
                )
        if not lines_to_split:
            raise UserError(_(
                "Hech qanday miqdor kiritilmadi.\n\n"
                "Kamida bitta rang uchun o'lcham qatori qo'shib, miqdorni "
                "kiriting. Bu qabulda o'lchamga bo'linadigan tovar bo'lmasa "
                "— sehrgarni yopib, hujjatni odatdagidek tasdiqlayvering."))

        # 2-bosqich: faqat miqdor kiritilgan qatorlarni bo'lamiz
        for line in lines_to_split:
            line._apply()
        return {"type": "ir.actions.act_window_close"}


class SizeDistributionWizardLine(models.TransientModel):
    _name = "feliza.size.distribution.wizard.line"
    _description = "Taqsimlash qatori (rang)"
    _rec_name = "product_id"

    wizard_id = fields.Many2one(
        "feliza.size.distribution.wizard", required=True, ondelete="cascade"
    )
    move_id = fields.Many2one("stock.move", string="Harakat", required=True)
    product_id = fields.Many2one("product.product", string="Tovar (rang)")
    demand_qty = fields.Float("Talab", digits="Product Unit of Measure")
    alloc_ids = fields.One2many(
        "feliza.size.distribution.wizard.alloc", "line_id", string="O'lchamlar"
    )
    allocated_qty = fields.Float(
        "Taqsimlandi",
        compute="_compute_allocated",
        digits="Product Unit of Measure",
    )
    remaining_qty = fields.Float(
        "Qoldi",
        compute="_compute_allocated",
        digits="Product Unit of Measure",
    )

    @api.depends("alloc_ids.quantity", "demand_qty")
    def _compute_allocated(self):
        for line in self:
            allocated = sum(line.alloc_ids.mapped("quantity"))
            line.allocated_qty = allocated
            line.remaining_qty = line.demand_qty - allocated

    def _target_variant(self, size_value):
        """Manba variantining rang(lar)i + berilgan o'lcham uchun mos
        variantni topadi; kerak bo'lsa, o'lchamni shablonga AVTOMATIK
        qo'shib, variantni ham avtomatik yaratadi (skladchidan qo'lda
        oldindan sozlash talab qilinmaydi)."""
        self.ensure_one()
        product = self.product_id
        template = product.product_tmpl_id
        non_size_ptav = product.product_template_attribute_value_ids.filtered(
            lambda ptav: not ptav.attribute_id.is_size
        )
        size_attribute_line = template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == size_value.attribute_id
        )[:1]
        if not size_attribute_line:
            size_attribute_line = self.env[
                "product.template.attribute.line"
            ].create(
                {
                    "product_tmpl_id": template.id,
                    "attribute_id": size_value.attribute_id.id,
                    "value_ids": [(6, 0, [size_value.id])],
                }
            )
        elif size_value not in size_attribute_line.value_ids:
            size_attribute_line.write({"value_ids": [(4, size_value.id, 0)]})
        size_ptav = template.attribute_line_ids.mapped(
            "product_template_value_ids"
        ).filtered(
            lambda ptav: ptav.attribute_id == size_value.attribute_id
            and ptav.product_attribute_value_id == size_value
        )
        combination = non_size_ptav | size_ptav
        variant = template._get_variant_for_combination(combination)
        if not variant:
            variant = template._create_product_variant(combination)
        if not variant:
            raise UserError(
                _("'%(product)s' uchun '%(size)s' o'lchamli variant "
                  "yaratilmadi.\n\n"
                  "Buning odatiy sababi: '%(attribute)s' atributining "
                  "'Yaratish rejimi' sozlamasi 'Hech qachon' (Never) qilib "
                  "qo'yilgan. Buni tekshiring: Atributlar → '%(attribute)s' "
                  "→ 'Tip отображения' ostidagi 'Yaratish rejimi' "
                  "('Создание вариации') - u 'Немедленно' yoki 'Динамически' "
                  "bo'lishi kerak, 'Никогда' emas.",
                  product=template.display_name,
                  size=size_value.display_name,
                  attribute=size_value.attribute_id.display_name)
            )
        return variant

    def _apply(self):
        """Manba harakatini o'lchamlar bo'yicha bo'ladi."""
        self.ensure_one()
        move = self.move_id
        allocs = self.alloc_ids.filtered(lambda a: a.quantity > 0)
        if not allocs:
            return
        move._do_unreserve()

        new_moves = self.env["stock.move"]
        first = allocs[0]
        for alloc in allocs[1:]:
            variant = self._target_variant(alloc.size_value_id)
            new_moves |= move.copy(
                {
                    "product_id": variant.id,
                    "product_uom_qty": alloc.quantity,
                    "product_uom": variant.uom_id.id,
                    "move_line_ids": [(5, 0, 0)],
                }
            )
        first_variant = self._target_variant(first.size_value_id)
        move.write(
            {
                "product_id": first_variant.id,
                "product_uom_qty": first.quantity,
                "product_uom": first_variant.uom_id.id,
            }
        )
        if new_moves:
            new_moves._action_confirm(merge=False)
        (move | new_moves)._action_assign()


class SizeDistributionWizardAlloc(models.TransientModel):
    _name = "feliza.size.distribution.wizard.alloc"
    _description = "O'lcham taqsimoti katagi"
    _order = "line_id, size_value_id"

    line_id = fields.Many2one(
        "feliza.size.distribution.wizard.line",
        required=True,
        ondelete="cascade",
    )
    wizard_id = fields.Many2one(
        related="line_id.wizard_id", store=True, string="Sehrgar"
    )
    product_id = fields.Many2one(
        related="line_id.product_id", store=True, string="Tovar (rang)"
    )
    demand_qty = fields.Float(
        related="line_id.demand_qty", string="Talab"
    )
    remaining_qty = fields.Float(
        related="line_id.remaining_qty", string="Rang bo'yicha qoldi"
    )
    size_value_id = fields.Many2one(
        "product.attribute.value", string="O'lcham", required=True
    )
    quantity = fields.Float("Miqdor", digits="Product Unit of Measure")
