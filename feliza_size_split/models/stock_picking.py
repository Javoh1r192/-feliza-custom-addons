# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _size_split_eligible_moves(self):
        """Ushbu qabuldagi taqsimlashga mos harakatlarni qaytaradi.

        Harakat mos deb hisoblanadi, agar:
          * uning tovar shabloni O'lcham atributiga ega bo'lsa;
          * va tovar variantining o'lcham qiymati 'belgilanmagan'
            (is_size_placeholder) bo'lsa.
        """
        self.ensure_one()
        moves = self.env["stock.move"]
        for move in self.move_ids:
            if move.state in ("done", "cancel"):
                continue
            product = move.product_id
            template = product.product_tmpl_id
            # Shablonda o'lcham atributi bormi?
            if not template.attribute_line_ids.filtered(
                lambda line: line.attribute_id.is_size
            ):
                continue
            # Variantning o'lcham qiymati 'belgilanmagan'mi?
            size_values = product.product_template_attribute_value_ids.filtered(
                lambda ptav: ptav.attribute_id.is_size
            ).product_attribute_value_id
            if any(value.is_size_placeholder for value in size_values):
                moves |= move
        return moves

    def action_open_size_distribution(self):
        """Qabul ekranidagi "O'lchamlarga taqsimlash" tugmasi."""
        self.ensure_one()
        if self.picking_type_code != "incoming":
            raise UserError(
                _("O'lchamga taqsimlash faqat kiruvchi qabullar (Поступления) "
                  "uchun ishlaydi.")
            )
        moves = self._size_split_eligible_moves()
        if not moves:
            raise UserError(
                _("Taqsimlash uchun mos qator topilmadi.\n\n"
                  "Buning uchun tovar shablonida O'lcham atributi bo'lishi va "
                  "uning 'belgilanmagan' qiymati tanlangan bo'lishi kerak.\n"
                  "Konfiguratsiyani tekshiring: Atributlar → O'lcham → "
                  "'O'lcham atributi' va 'Belgilanmagan o'lcham' bayroqlari.")
            )
        wizard = self.env["feliza.size.distribution.wizard"].create(
            {"picking_id": self.id}
        )
        wizard._populate_from_picking()
        return {
            "type": "ir.actions.act_window",
            "name": _("O'lchamlarga taqsimlash"),
            "res_model": "feliza.size.distribution.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
