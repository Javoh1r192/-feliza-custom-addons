# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .feliza_numbering import (PARAM_ARTIKUL, PARAM_AUTO_ARTIKUL,
                               PARAM_AUTO_BARCODE, PARAM_BARCODE, auto_on,
                               make_ean13)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ------------------------------------------------------------------ #
    #  Avto berishni yoqish / o'chirish                                   #
    # ------------------------------------------------------------------ #
    #  DIQQAT: bu ikkisi ataylab `config_parameter` EMAS.
    #  Odoo `config_parameter` bo'lgan belgilash olib tashlanganda
    #  parametrni butunlay o'chirib yuboradi — keyin «parametr yo'q»
    #  degani «yoqilganmi yoki o'chirilganmi?» — bilib bo'lmaydi.
    #  Shuning uchun qiymatni o'zimiz «1» / «0» qilib yozamiz:
    #  parametr yo'q bo'lsa — yangi o'rnatish, ya'ni YOQILGAN.
    feliza_auto_artikul = fields.Boolean(
        string="Artikulni avtomat berish", default=True,
        help="O'chirilsa — zakup oynasida yangi mahsulotga artikul "
             "berilmaydi, xodim o'zi qo'lda kiritadi. Mavjud "
             "mahsulotlarning artikuliga bu sozlama ta'sir qilmaydi.")

    feliza_auto_barcode = fields.Boolean(
        string="Barkodni avtomat berish", default=True,
        help="O'chirilsa — yangi variantlarga barkod berilmaydi, "
             "xodim o'zi qo'lda kiritadi yoki tashqi barkodni "
             "yopishtiradi.")

    feliza_birka_kod_turi = fields.Selection(
        [("bar", "Chiziqli barkod (EAN-13)"), ("qr", "QR kod")],
        string="Birkadagi kod turi", default="bar",
        config_parameter="feliza.birka.kod_turi",
        help="Birkada chiziqli barkod yoki QR kod chiqishini tanlaydi. "
             "Default — chiziqli barkod (o'zgarmaydi).")

    feliza_last_artikul = fields.Char(
        string="Oxirgi ishlatilgan artikul",
        config_parameter=PARAM_ARTIKUL,
        help="Zakupda yangi mahsulot yaratilganda artikul shu raqamdan "
             "keyingisidan boshlab beriladi. Band raqamlar o'tkazib "
             "yuboriladi. Artikul mahsulotga bitta — nechta variant "
             "yaratilsa ham o'zgarmaydi.")

    feliza_last_barcode = fields.Char(
        string="Oxirgi ishlatilgan barkod",
        config_parameter=PARAM_BARCODE,
        help="13 xonali EAN-13 barkod. Har bir yangi VARIANTGA shu "
             "raqamdan keyingi bo'sh barkod beriladi. Nazorat raqami "
             "avtomat hisoblanadi — skaner o'qiydigan haqiqiy EAN-13.")

    # Sozlamalar oynasida to'g'ridan-to'g'ri tahrirlash uchun.
    # `res.config.settings` — vaqtinchalik model, shuning uchun oddiy
    # one2many bo'lmaydi: seriyalarni compute bilan olib kelamiz.
    feliza_artikul_series_ids = fields.Many2many(
        "feliza.artikul.series", string="Artikul seriyalari",
        compute="_compute_feliza_series", readonly=False)

    feliza_next_artikul_preview = fields.Char(
        string="Keyingi artikul", readonly=True,
        compute="_compute_feliza_preview")
    feliza_next_barcode_preview = fields.Char(
        string="Keyingi barkod", readonly=True,
        compute="_compute_feliza_preview")

    def _compute_feliza_series(self):
        series = self.env["feliza.artikul.series"].search([])
        for rec in self:
            rec.feliza_artikul_series_ids = series

    # ------------------------------------------------------------------ #
    #  Yoqish/o'chirish qiymatlarini o'qish va saqlash                    #
    # ------------------------------------------------------------------ #
    @api.model
    def get_values(self):
        res = super().get_values()
        res.update(
            feliza_auto_artikul=auto_on(self.env, PARAM_AUTO_ARTIKUL),
            feliza_auto_barcode=auto_on(self.env, PARAM_AUTO_BARCODE),
        )
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param(PARAM_AUTO_ARTIKUL,
                      "1" if self.feliza_auto_artikul else "0")
        ICP.set_param(PARAM_AUTO_BARCODE,
                      "1" if self.feliza_auto_barcode else "0")

    @api.depends("feliza_last_artikul", "feliza_last_barcode")
    def _compute_feliza_preview(self):
        """Kiritilgan raqamdan keyin nima chiqishini darhol ko'rsatadi.

        Bu shunchaki ko'rsatish — hech narsa band qilinmaydi va navbat
        surilmaydi. Xodim raqamni to'g'ri kiritganiga ishonch hosil qiladi.
        """
        for rec in self:
            art = "".join(ch for ch in (rec.feliza_last_artikul or "")
                          if ch.isdigit())
            rec.feliza_next_artikul_preview = str(int(art) + 1) if art else ""
            bc = "".join(ch for ch in (rec.feliza_last_barcode or "")
                         if ch.isdigit())
            rec.feliza_next_barcode_preview = (
                make_ean13(int(bc[:12]) + 1) if len(bc) >= 12 else "")

    @api.constrains("feliza_last_barcode")
    def _check_feliza_last_barcode(self):
        for rec in self:
            v = rec.feliza_last_barcode
            if not v:
                continue
            digits = "".join(ch for ch in v if ch.isdigit())
            if len(digits) != 13:
                raise ValidationError(_(
                    "Barkod 13 xonali bo'lishi kerak (EAN-13). "
                    "Siz kiritdingiz: %s (%s xona)") % (v, len(digits)))
            if make_ean13(int(digits[:12])) != digits:
                raise ValidationError(_(
                    "«%s» — EAN-13 nazorat raqami noto'g'ri. "
                    "To'g'risi: %s.\n\nBarkodni birkadan ko'chirganda "
                    "oxirgi raqam tushib qolmaganiga ishonch hosil qiling."
                ) % (digits, make_ean13(int(digits[:12]))))

    @api.constrains("feliza_last_artikul")
    def _check_feliza_last_artikul(self):
        for rec in self:
            v = (rec.feliza_last_artikul or "").strip()
            if not v:
                continue
            if not v.isdigit():
                raise ValidationError(_(
                    "Artikul faqat raqamlardan iborat bo'lishi kerak. "
                    "Siz kiritdingiz: %s") % v)
            # «3» kabi qiymat kiritilib qolsa, undan «4» degan artikul
            # chiqib ketardi. Feliza artikuli har doim 6 xonali.
            if len(v) < 6:
                raise ValidationError(_(
                    "Artikul 6 xonali bo'lishi kerak. Siz kiritdingiz: "
                    "«%s».\n\nBu maydon — kategoriyasi seriyaga "
                    "biriktirilmagan tovarlar uchun zaxira navbat. "
                    "Odatda uni bo'sh qoldirish to'g'riroq: har bir "
                    "kategoriya o'z seriyasidan yuradi.") % v)
