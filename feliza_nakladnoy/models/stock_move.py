# -*- coding: utf-8 -*-
"""HUJJAT QATORI UCHUN MA'LUMOT

Nakladnoyda tovar nomi, artikuli, rangi va o'lchami ALOHIDA
ustunlarda turishi kerak. Odoo'da esa ularning hammasi bitta
`display_name` ichida qorishib ketadi: «Test -1 (гр.роз, .)».

Bu yerdagi maydonlar o'sha ma'lumotni ajratib beradi. Hammasi
hisoblanadigan va SAQLANMAYDIGAN — bazaga bitta ustun ham
qo'shilmaydi, faqat hujjat chop etilayotganda hisoblanadi.
"""
from odoo import api, fields, models

# Atribut nomlari bazada har xil yozilgan: «rang», «цвет», «Rang».
RANG = ("rang", "цвет", "color")
OLCHAM = ("lcham", "размер", "size", "razmer")


def feliza_pul(qiymat):
    """So'm: tiyinsiz, mingliklar probel bilan — 825 000."""
    return "{:,.0f}".format(qiymat or 0.0).replace(",", "\u00a0")


def feliza_son(qiymat):
    """Dona: butun bo'lsa kasrsiz, aks holda ikki xona."""
    qiymat = qiymat or 0.0
    if abs(qiymat - round(qiymat)) < 0.0001:
        return "{:,.0f}".format(qiymat).replace(",", "\u00a0")
    return "{:,.2f}".format(qiymat).replace(",", "\u00a0")


class StockMove(models.Model):
    _inherit = "stock.move"

    feliza_artikul = fields.Char(
        string="Artikul", compute="_compute_feliza_nakladnoy")
    feliza_rang = fields.Char(
        string="Rang", compute="_compute_feliza_nakladnoy")
    feliza_olcham = fields.Char(
        string="O'lcham", compute="_compute_feliza_nakladnoy")
    feliza_nomi = fields.Char(
        string="Tovar nomi", compute="_compute_feliza_nakladnoy",
        help="Rang va o'lchamsiz, sof nom — ular alohida ustunda.")
    feliza_narx = fields.Float(
        string="Sotish narxi", digits="Product Price",
        compute="_compute_feliza_nakladnoy")
    feliza_soni = fields.Float(
        string="Soni", digits="Product Unit",
        compute="_compute_feliza_nakladnoy",
        help="Hujjat yakunlangan bo'lsa — haqiqiy miqdor, aks holda talab.")
    feliza_summa = fields.Monetary(
        string="Summa", currency_field="company_currency_id",
        compute="_compute_feliza_nakladnoy")
    company_currency_id = fields.Many2one(
        "res.currency", compute="_compute_feliza_nakladnoy")

    # Chop etish uchun tayyor matn. Nega maydon? Chunki so'mda tiyin
    # yo'q va mingliklar probel bilan ajratilishi kerak — buni QWeb
    # ichida yozsak shablon o'qib bo'lmas holga kelardi.
    feliza_joy = fields.Char(
        string="Joylashuv", compute="_compute_feliza_nakladnoy",
        help="Kiruvchi hujjatda — tovar QAYERGA qo'yiladi; "
             "chiquvchida — QAYERDAN olinadi.")
    feliza_talab_matn = fields.Char(compute="_compute_feliza_nakladnoy")
    feliza_soni_matn = fields.Char(compute="_compute_feliza_nakladnoy")
    feliza_narx_matn = fields.Char(compute="_compute_feliza_nakladnoy")
    feliza_summa_matn = fields.Char(compute="_compute_feliza_nakladnoy")

    @staticmethod
    def _feliza_joy_qisqa(location, ombor_kodi):
        """Lokatsiya nomini qisqartiradi.

        To'liq nom «Asosi/Stock/A-1» ko'rinishida bo'ladi. Ombor nomi
        hujjatning tepasida allaqachon yozilgan, shuning uchun uni
        takrorlamaymiz: «Stock/A-1» qoladi. Tovarlar keyinchalik
        javonlarga ajratilganda ham shu ustun to'g'ri ishlaydi.
        """
        nom = location.complete_name or location.name or ""
        if ombor_kodi and nom.startswith(ombor_kodi + "/"):
            nom = nom[len(ombor_kodi) + 1:]
        elif "/" in nom:
            nom = nom.split("/", 1)[1]
        return nom

    @api.depends("product_id", "product_uom_qty", "quantity", "state",
                 "move_line_ids.location_id", "move_line_ids.location_dest_id")
    def _compute_feliza_nakladnoy(self):
        for move in self:
            product = move.product_id
            move.company_currency_id = (
                move.company_id or self.env.company).currency_id
            move.feliza_nomi = product.product_tmpl_id.name or ""
            move.feliza_artikul = (
                product.default_code or product.product_tmpl_id.default_code or "")

            rang = olcham = ""
            qoshimcha = []
            for val in product.product_template_attribute_value_ids:
                atr = (val.attribute_id.name or "").strip().lower()
                if any(k in atr for k in RANG):
                    rang = val.name
                elif any(k in atr for k in OLCHAM):
                    olcham = val.name
                else:
                    qoshimcha.append(val.name)
            # boshqa atributlar (masalan «material») yo'qolib ketmasin —
            # ular nomga qo'shiladi, chunki o'z ustuni yo'q
            if qoshimcha:
                move.feliza_nomi = "%s (%s)" % (
                    move.feliza_nomi, ", ".join(qoshimcha))
            move.feliza_rang = rang
            move.feliza_olcham = olcham

            move.feliza_narx = product.lst_price or 0.0
            miqdor = move.quantity if move.state == "done" else move.product_uom_qty
            move.feliza_soni = miqdor
            move.feliza_summa = (move.feliza_narx or 0.0) * (miqdor or 0.0)

            # --- joylashuv ---
            kod = move.picking_type_id.code
            qatorlar = move.move_line_ids
            if kod == "outgoing":
                joylar = qatorlar.mapped("location_id") or move.location_id
                ombor = move.location_id.warehouse_id
            else:
                joylar = qatorlar.mapped("location_dest_id") or move.location_dest_id
                ombor = move.location_dest_id.warehouse_id
            kodi = ombor.code if ombor else ""
            nomlar = []
            for joy in joylar:
                nom = self._feliza_joy_qisqa(joy, kodi)
                if nom and nom not in nomlar:
                    nomlar.append(nom)
            move.feliza_joy = ", ".join(nomlar) or "—"

            move.feliza_talab_matn = feliza_son(move.product_uom_qty)
            move.feliza_soni_matn = feliza_son(miqdor)
            move.feliza_narx_matn = feliza_pul(move.feliza_narx)
            move.feliza_summa_matn = feliza_pul(move.feliza_summa)
