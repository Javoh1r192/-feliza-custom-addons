# -*- coding: utf-8 -*-
"""
SAVDO REJASI
============
Odoo'da do'kon bo'yicha oylik savdo rejasi saqlanadigan standart model
yo'q. Shuning uchun shu yerda yaratamiz.

Reja OYLIK kiritiladi. Kunlik reja undan hisoblanadi — lekin oddiy
"oylik / kunlar soni" emas: savdo hafta kunlariga qarab keskin farq
qiladi (shanba dushanbadan ~2 barobar ko'p), shuning uchun haftalik
og'irlik koeffitsiyenti qo'llaniladi.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Hafta kunlari og'irligi (0=dushanba ... 6=yakshanba).
# Kiyim savdosi uchun tipik taqsimot; sozlash mumkin.
DOW_WEIGHT = {0: 0.78, 1: 0.85, 2: 0.90, 3: 0.98, 4: 1.18, 5: 1.40, 6: 1.30}


class FelizaSalesTarget(models.Model):
    _name = "feliza.sales.target"
    _description = "Feliza — do'kon oylik savdo rejasi"
    _order = "date_month desc, config_id"
    _rec_name = "display_name"

    config_id = fields.Many2one(
        "pos.config", string="Do'kon (kassa)", required=True, ondelete="cascade",
        help="Reja shu kassaga biriktiriladi. Bitta do'konda bir nechta "
             "kassa bo'lsa, har biriga alohida reja kiriting yoki "
             "kassalarni «Do'kon guruhi» maydoni orqali birlashtiring.")
    date_month = fields.Date(
        string="Oy", required=True,
        help="Oyning istalgan sanasi — tizim oy boshiga keltiradi.")
    amount = fields.Monetary(
        string="Oylik reja", required=True, currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", string="Valyuta",
        default=lambda s: s.env.company.currency_id.id, required=True)
    company_id = fields.Many2one(
        "res.company", string="Kompaniya",
        default=lambda s: s.env.company.id, required=True)
    note = fields.Char(string="Izoh")

    @api.depends("config_id", "date_month")
    def _compute_display_name(self):
        """Odoo'ning standart display_name maydonini to'ldiramiz."""
        for rec in self:
            if rec.config_id and rec.date_month:
                rec.display_name = "%s — %s" % (
                    rec.config_id.name, rec.date_month.strftime("%m.%Y"))
            else:
                rec.display_name = _("Yangi reja")

    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("date_month"):
                vals["date_month"] = fields.Date.from_string(
                    vals["date_month"]).replace(day=1)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("date_month"):
            vals["date_month"] = fields.Date.from_string(
                vals["date_month"]).replace(day=1)
        return super().write(vals)

    @api.constrains("config_id", "date_month", "company_id")
    def _check_unique(self):
        for rec in self:
            dup = self.search_count([
                ("id", "!=", rec.id),
                ("config_id", "=", rec.config_id.id),
                ("date_month", "=", rec.date_month),
                ("company_id", "=", rec.company_id.id),
            ])
            if dup:
                raise ValidationError(_(
                    "«%s» do'koni uchun %s oyiga reja allaqachon kiritilgan. "
                    "Ikkita reja bo'lishi mumkin emas."
                ) % (rec.config_id.name, rec.date_month.strftime("%m.%Y")))

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError(_("Reja manfiy bo'lishi mumkin emas."))

    # ------------------------------------------------------------------ #
    #  Hisoblash yordamchilari                                             #
    # ------------------------------------------------------------------ #
    @api.model
    def get_month_target(self, config_ids, date_in):
        """Berilgan kassalar uchun oylik rejalar yig'indisi."""
        if not config_ids:
            return 0.0
        month_start = fields.Date.to_date(date_in).replace(day=1)
        recs = self.sudo().search([
            ("config_id", "in", list(config_ids)),
            ("date_month", "=", month_start),
        ])
        return sum(recs.mapped("amount"))

    @api.model
    def get_day_target(self, config_ids, date_in):
        """Kunlik reja — oylik rejadan hafta kunlari og'irligi bo'yicha.

        Oddiy "oylik / 30" emas, chunki shanba savdosi dushanbadan
        ~1,8 barobar ko'p. Aks holda dam olish kunlari reja doim
        "bajarilgan", ish kunlari doim "bajarilmagan" ko'rinardi.
        """
        import calendar

        month_total = self.get_month_target(config_ids, date_in)
        if not month_total:
            return 0.0

        d = fields.Date.to_date(date_in)
        days_in_month = calendar.monthrange(d.year, d.month)[1]

        # oydagi barcha kunlar og'irliklari yig'indisi
        total_weight = 0.0
        for day in range(1, days_in_month + 1):
            dow = d.replace(day=day).weekday()
            total_weight += DOW_WEIGHT.get(dow, 1.0)

        if not total_weight:
            return month_total / days_in_month

        return month_total * DOW_WEIGHT.get(d.weekday(), 1.0) / total_weight

    @api.model
    def get_period_target(self, config_ids, date_from, date_to):
        """Ixtiyoriy davr uchun reja — kunlik rejalar yig'indisi."""
        from datetime import timedelta

        d_from = fields.Date.to_date(date_from)
        d_to = fields.Date.to_date(date_to)
        total = 0.0
        cur = d_from
        # xavfsizlik: 400 kundan ortiq davrni hisoblamaymiz
        guard = 0
        while cur <= d_to and guard < 400:
            total += self.get_day_target(config_ids, cur)
            cur += timedelta(days=1)
            guard += 1
        return total

    # ------------------------------------------------------------------ #
    def action_copy_previous_month(self):
        """O'tgan oy rejasini joriy oyga nusxalash (qulaylik uchun)."""
        from dateutil.relativedelta import relativedelta

        created = 0
        for rec in self:
            nxt = rec.date_month + relativedelta(months=1)
            exists = self.search_count([
                ("config_id", "=", rec.config_id.id),
                ("date_month", "=", nxt),
            ])
            if not exists:
                rec.copy({"date_month": nxt})
                created += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Nusxalandi"),
                "message": _("%s ta reja keyingi oyga nusxalandi.") % created,
                "type": "success",
                "sticky": False,
            },
        }
