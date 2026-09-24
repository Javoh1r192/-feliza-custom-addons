# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    wallet_currency_id = fields.Many2one(
        "res.currency", string="Hamyon valyutasi", compute="_compute_wallet_currency_id"
    )
    wallet_balance = fields.Monetary(
        string="Cashback balansi",
        currency_field="wallet_currency_id",
        compute="_compute_wallet_balance",
        help="Mijozning joriy cashback balansi — Odoo'ning o'z Loyalty "
        "dasturidagi ('Sozlamalar > Mijoz hamyoni' bo'limida tanlangan) "
        "ball balansi, so'mga aylantirilgan holda. Faqat ko'rish uchun: "
        "bu yerda to'g'ridan-to'g'ri tahrirlanmaydi — o'zgartirish uchun "
        "loyalty kartaning o'zidagi 'Update Balance' amalidan foydalaning.",
    )

    def _compute_wallet_currency_id(self):
        for partner in self:
            partner.wallet_currency_id = self.env.company.currency_id

    def _compute_wallet_balance(self):
        for partner in self:
            program = partner._wallet_get_program()
            card = partner._wallet_get_card(program) if program else False
            rate = partner._wallet_point_rate(program) if program else 1.0
            partner.wallet_balance = (card.points * rate) if card else 0.0

    def action_view_wallet_card(self):
        """Mijozning cashback loyalty kartasini (native Odoo ekranida)
        ochadi — balans tarixi shu yerda, 'History' bo'limida ko'rinadi.
        """
        self.ensure_one()
        program = self._wallet_get_program()
        card = self._wallet_get_card(program) if program else False
        action = {
            "type": "ir.actions.act_window",
            "name": _("Cashback karta"),
            "res_model": "loyalty.card",
            "context": {"default_partner_id": self.id, "default_program_id": program.id if program else False},
        }
        if card:
            action.update({"view_mode": "form", "res_id": card.id})
        else:
            action.update({"view_mode": "list,form", "domain": [("partner_id", "=", self.id)]})
        return action

    def _wallet_get_program(self):
        """Sozlamalarda tanlangan cashback Loyalty dasturi."""
        return self.env.company.pos_wallet_loyalty_program_id

    def _wallet_get_card(self, program):
        """Ushbu mijozning berilgan dastur bo'yicha loyalty kartasi (bo'lsa)."""
        self.ensure_one()
        if not program:
            return self.env["loyalty.card"]
        return self.env["loyalty.card"].sudo().search([
            ("partner_id", "=", self.id),
            ("program_id", "=", program.id),
        ], limit=1)

    def _wallet_point_rate(self, program):
        """1 ball nechchi so'mga teng ekanini dastur mukofot (reward)
        sozlamasidan dinamik o'qiydi (qattiq kod qilib yozilmagan — admin
        Loyalty dasturidagi nisbatni o'zgartirsa, bu yerda ham avtomatik
        moslashadi). Standart Odoo 'Cashback' shabloni odatda 1 ball = 1
        valyuta birligi qilib sozlanadi.
        """
        if not program:
            return 1.0
        reward = self.env["loyalty.reward"].sudo().search([
            ("program_id", "=", program.id),
            ("reward_type", "=", "discount"),
            ("discount_mode", "=", "per_point"),
        ], limit=1)
        if reward and reward.discount:
            return reward.discount
        _logger.warning(
            "Cashback loyalty dasturi (%s) uchun 'per_point' turidagi mukofot "
            "topilmadi — 1 ball = 1 valyuta birligi deb hisoblanmoqda. "
            "Sozlamalarni tekshiring.", program.display_name,
        )
        return 1.0

    def _wallet_spend(self, amount, order=False):
        """Mijozning cashback loyalty kartasidan ``amount`` (valyutada)
        summaga teng ball miqdorini xavfsiz yechadi.

        Bir nechta POS terminal bir vaqtda yozishi mumkin bo'lgani uchun
        qator darajasidagi ``FOR UPDATE`` lock bilan race condition oldini
        oladi. Native Odoo bilan bir xil uslubda (``loyalty.history``)
        audit yozuvi qoldiradi, shunda mijozning karta tarixi standart
        Odoo ekranlarida (Loyalty Cards > karta > History) to'g'ri ko'rinadi.

        :return: haqiqatda yechilgan ball miqdori.
        """
        self.ensure_one()
        if not amount:
            return 0.0

        program = self._wallet_get_program()
        if not program:
            raise UserError(_(
                "Cashback uchun Loyalty dasturi sozlanmagan. Point of Sale > "
                "Konfiguratsiya > Sozlamalar > 'Mijoz hamyoni (Cashback)' "
                "bo'limida dasturni tanlang."
            ))

        card = self._wallet_get_card(program)
        if not card:
            raise UserError(_(
                "%(partner)s uchun '%(program)s' dasturi bo'yicha hamyon "
                "kartasi topilmadi (balans 0).",
                partner=self.display_name, program=program.display_name,
            ))

        rate = self._wallet_point_rate(program)
        points_to_use = (amount / rate) if rate else 0.0

        # MUHIM: xom SQL SELECT'dan OLDIN ORM keshini albatta flush qilish
        # kerak. Sabab: Odoo ORM'ning write() metodi SQL UPDATE'ni DARHOL
        # bazaga yubormaydi -- u xotiradagi keshda "flush qilinishi kerak"
        # deb belgilanib qoladi va faqat keyinroq (masalan flush_all() yoki
        # avtomatik flush nuqtalarida) haqiqiy bazaga yoziladi. Bizning
        # confirm_coupon_programs() ulanishimiz endi native "ball TO'PLASH"
        # (earn, card.points'ni ORM write() orqali oshiradi) tugagandan
        # KEYIN ishga tushadi -- lekin agar shu yerdagi xom SQL SELECT
        # oldin flush qilinmasa, u native'ning hali bazaga yozilmagan
        # ORM yozuvini "ko'rmaydi" va ESKI (earn'dan oldingi) balansni
        # o'qib oladi -- natijada yakuniy balans NOTO'G'RI chiqadi
        # (lokal sinovda aniq tasdiqlangan xato: earn 34500 ball qo'shgan
        # bo'lsa ham, spend hisob-kitobi buni hisobga olmay, balansni
        # noto'g'ri 0'ga tushirib qo'ygan edi). flush_all() bu muammoni
        # butunlay yo'qotadi: undan keyin xom SQL ham, ORM ham bir xil,
        # bazadagi eng so'nggi holatni ko'radi.
        self.env.flush_all()

        self.env.cr.execute(
            "SELECT points FROM loyalty_card WHERE id = %s FOR UPDATE", (card.id,)
        )
        row = self.env.cr.fetchone()
        current_points = (row and row[0]) or 0.0

        if points_to_use > current_points:
            # MUHIM (xavfsizlik bilan bog'liq qaror): ilgari bu yerda jim
            # ravishda mavjud miqdorga "kesib" (clamp) qo'yib, savdoni
            # baribir "to'liq to'langan" deb yakunlardik. Jonli sinovda
            # aniqlandiki, bu JIDDIY moliyaviy xato edi: POS frontendidagi
            # "Cashback" balans ko'rsatkichi bitta sessiya ichida (backendga
            # qayta ulanmasdan) SPEND'larni hisobga olmay, ESKIRGAN va
            # OShIRILGAN raqam ko'rsatishi mumkin edi (masalan, haqiqiy
            # balans 55 bo'lsa-yu, frontend eski keshlangan 555 ni
            # ko'rsatishi). Kassir shu noto'g'ri raqamga tayanib to'lov
            # qatoriga 555 kiritsa, avvalgi kod kartadan faqat 55-56 ball
            # yechib, LEKIN to'lov qatorida "Cashback: 555 so'm" deb
            # QOLDIRARDI — Odoo buni "muvozanatlash" uchun avtomatik
            # -455 so'mlik soxta naqd "qaytim" qatorini yaratardi. Natijada
            # kunlik "Cashback" to'lov usuli hisoboti va kassa hisob-kitobi
            # haqiqiy holatga mos kelmay qolardi (real pul/ball zaxirasi
            # bilan qoplanmagan "sotuv").
            #
            # Shuning uchun endi bunday nomuvofiqlikni JIM O'TKAZIB
            # YUBORMAYMIZ — savdoni butunlay BLOKLAYMIZ. Bu RPC xatoga
            # olib keladi, frontend buyurtmani sinxronlamaydi (native
            # "ombordagi mahsulot yetarli emas" xatosi kabi), kassir
            # to'lov summasini mijozning ENDI YANGILANGAN haqiqiy
            # balansiga moslab qayta kiritishi kerak bo'ladi. Bu mijoz
            # balansini himoya qiladi VA to'lov yozuvlarining haqiqiyligini
            # kafolatlaydi.
            raise UserError(_(
                "%(partner)s uchun Cashback balansi yetarli emas: to'lov "
                "ekranida %(requested)s ball miqdorida so'ralgan, lekin "
                "mijozning haqiqiy joriy balansida faqat %(available)s "
                "ball bor. Buning sababi ko'pincha: POS oynasi ochiq "
                "turgan holda oldingi buyurtmalarda balansning bir qismi "
                "allaqachon ishlatilgan, lekin ekrandagi ko'rsatkich hali "
                "yangilanmagan. To'lov ekraniga qaytib, Cashback summasini "
                "to'g'rilang (yoki 'Orders' menyusi orqali qayta kiring, "
                "shunda balans yangilanadi) va qaytadan urinib ko'ring.",
                partner=self.display_name,
                requested=round(points_to_use, 2),
                available=round(current_points, 2),
            ))

        new_points = current_points - points_to_use
        # MUHIM: bu yerda ORM'ning write() metodidan foydalanamiz (xom SQL
        # UPDATE emas). Sabab: xom SQL yozuvi Odoo ORM keshini chetlab
        # o'tib, native pos_loyalty modulining O'SHA BUYURTMA uchun ball
        # TO'PLASH (earn) yozuvini (loyalty.history + card.points) shu
        # bitim ichida keyinroq yozishini "yo'qotib qo'yishi" aniqlandi
        # (jonli sinovda ikki marta takrorlanib tasdiqlangan xato: Cashback
        # orqali sarflangan buyurtmada earn umuman ishlamay qolgan edi).
        # ORM write() ishlatilsa, native kod bilan bir xil kesh/yozuv
        # kanali orqali ishlaydi va bu muammo yo'qoladi. FOR UPDATE lock
        # yuqorida xom SQL SELECT orqali olinadi (faqat o'qish/lock, keshga
        # tegmaydi) — race condition himoyasi saqlanib qoladi.
        card.sudo().write({"points": new_points})

        history_vals = {
            "card_id": card.id,
            "description": _("Cashback to'lov usuli orqali ishlatildi%s", order and _(" — buyurtma %s", order.name) or ""),
            "used": points_to_use,
            "issued": 0.0,
        }
        if order:
            history_vals.update({"order_model": order._name, "order_id": order.id})
        self.env["loyalty.history"].sudo().with_context(loyalty_no_mail=True).create(history_vals)

        return points_to_use
