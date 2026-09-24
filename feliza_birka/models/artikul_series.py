# -*- coding: utf-8 -*-
"""ARTIKUL SERIYALARI — KATEGORIYA BO'YICHA

Feliza'da artikul bitta uzluksiz raqam emas: har bir tovar guruhi o'z
seriyasidan boshlanadi. Bazadagi holat shuni ko'rsatdi:

    1xxxxx  kiyim (ustki, ostki, komplekt)   3 203 ta, oxirgisi 108092
    2xxxxx  paypoq / kolgotki                   78 ta, oxirgisi 200135
    3xxxxx  bijuteriya (soat, uzuk, zirak)       7 ta, oxirgisi 300017
    4xxxxx  atir                                272 ta, oxirgisi 400391
    5xxxxx  bosh kiyim, ro'mol, remen           347 ta, oxirgisi 500682
    6xxxxx  sumka                               132 ta, oxirgisi 600366
    7xxxxx  oyoq kiyim                          329 ta, oxirgisi 700719

DIQQAT — ikkita nozik joy bor:

1. Bir seriya BIR NECHTA kategoriyaga tegishli bo'lishi mumkin.
   «Верхняя одежда», «Нижняя одежда» va «Комплект» — uchalasi ham
   1xxxxx dan yuradi. Shuning uchun seriya asosiy yozuv, kategoriyalar
   esa unga biriktiriladi. Aks holda uchta alohida hisoblagich bir xil
   raqamni uch marta berib yuborardi.

2. Bola kategoriya otasidan boshqa seriyada bo'lishi mumkin.
   «Аксессуар» — 3xxxxx, lekin «Аксессуар / Сумка» — 6xxxxx.
   Shuning uchun qidiruv ENG AVVAL tovarning o'z kategoriyasidan
   boshlanadi va yuqoriga ko'tariladi: eng yaqin sozlangan kategoriya
   yutadi.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FelizaArtikulSeries(models.Model):
    _name = "feliza.artikul.series"
    _description = "Artikul seriyasi (kategoriya bo'yicha)"
    _order = "sequence, id"

    name = fields.Char(string="Seriya", required=True,
                       help="Masalan: «Kiyim (1xxxxx)»")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    categ_ids = fields.Many2many(
        "product.category", string="Kategoriyalar",
        help="Shu kategoriyalar VA ularning ichidagi bola kategoriyalar "
             "uchun artikul shu seriyadan beriladi. Bola kategoriya "
             "boshqa seriyaga biriktirilgan bo'lsa — o'sha kuchliroq.")

    last_code = fields.Char(
        string="Oxirgi ishlatilgan artikul", required=True,
        help="Yangi tovarga shu raqamdan keyingi BO'SH raqam beriladi. "
             "Band raqamlar o'tkazib yuboriladi.")

    next_code = fields.Char(string="Keyingisi", compute="_compute_next_code")

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Bunday nomli seriya allaqachon bor."),
    ]

    @api.depends("last_code")
    def _compute_next_code(self):
        for rec in self:
            digits = "".join(c for c in (rec.last_code or "") if c.isdigit())
            rec.next_code = str(int(digits) + 1) if digits else ""

    @api.constrains("last_code")
    def _check_last_code(self):
        for rec in self:
            v = (rec.last_code or "").strip()
            if not v.isdigit():
                raise ValidationError(_(
                    "«%s» seriyasidagi artikul faqat raqamlardan iborat "
                    "bo'lishi kerak. Siz kiritdingiz: %s") % (rec.name, v))

    @api.constrains("categ_ids")
    def _check_categ_unique(self):
        """Bitta kategoriya ikkita seriyaga biriktirilmasin.

        Aks holda qaysi raqam berilishi tasodifga qolardi.
        """
        for rec in self:
            if not rec.categ_ids:
                continue
            other = self.search([
                ("id", "!=", rec.id),
                ("categ_ids", "in", rec.categ_ids.ids),
            ], limit=1)
            if other:
                clash = rec.categ_ids & other.categ_ids
                raise ValidationError(_(
                    "«%(categ)s» kategoriyasi «%(a)s» va «%(b)s» "
                    "seriyalarining ikkalasida ham bor. Bittasidan "
                    "olib tashlang.") % {
                        "categ": ", ".join(clash.mapped("complete_name")),
                        "a": rec.name, "b": other.name})

    # ------------------------------------------------------------------ #
    @api.model
    def series_for_category(self, categ):
        """Kategoriyaga mos seriyani topadi (eng yaqinidan yuqoriga).

        `product.category.parent_path` — «53/58/» ko'rinishidagi yo'l.
        Uni teskari o'qib, birinchi mos kelgan seriyani qaytaramiz:
        avval tovarning o'z kategoriyasi, keyin otasi, keyin bobosi.
        """
        if not categ:
            return self.browse()
        path = (categ.sudo().parent_path or "").strip("/")
        ids = [int(x) for x in path.split("/") if x.isdigit()] if path else []
        if categ.id not in ids:
            ids.append(categ.id)
        for cid in reversed(ids):          # eng yaqin kategoriyadan boshlab
            series = self.sudo().search([("categ_ids", "in", cid)], limit=1)
            if series:
                return series
        return self.browse()
