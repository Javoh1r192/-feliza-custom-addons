# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    wallet_used_amount = fields.Monetary(
        string="Ishlatilgan cashback",
        compute="_compute_wallet_used_amount",
        store=True,
        help="Ushbu buyurtmada 'Cashback' to'lov usuli orqali to'langan summa.",
    )
    wallet_processed = fields.Boolean(
        string="Hamyon amali bajarildi", default=False, copy=False, readonly=True,
        help="Ichki bayroq: bir buyurtma uchun cashback loyalty kartasidan "
        "yechish faqat bir marta bajarilishini kafolatlaydi (qayta "
        "sinxronlashda ikki marta yechilib ketmasligi uchun).",
    )

    @api.depends("payment_ids", "payment_ids.amount", "payment_ids.payment_method_id.is_wallet_payment")
    def _compute_wallet_used_amount(self):
        for order in self:
            order.wallet_used_amount = sum(
                p.amount for p in order.payment_ids if p.payment_method_id.is_wallet_payment
            )

    def confirm_coupon_programs(self, coupon_data):
        """MUHIM: bu yerga ULANAMIZ (action_pos_order_paid'ga emas)!

        Jonli sinovda aniqlangan tub sabab: Odoo'ning o'z pos_loyalty
        moduli (confirm_coupon_programs -> _remove_duplicate_coupon_data)
        "ushbu buyurtma + dastur uchun loyalty.history YOZUVI ALLAQACHON
        bormi?" tekshiruvini o'tkazadi va agar bo'lsa, ball TO'PLASHNI
        (earn) "dublikat" deb hisoblab, umuman qo'shmay o'tkazib yuboradi.

        Agar biz cashback SARFLASH tarixini (_wallet_spend orqali
        loyalty.history) shu tekshiruvdan OLDIN yaratib qo'ysak (masalan,
        action_pos_order_paid orqali — bu confirm_coupon_programs'dan
        OLDINROQ ishga tushishi aniqlandi), native kod bizning "used"
        yozuvimizni o'zining "earn allaqachon qo'shilgan" belgisi deb
        noto'g'ri tushunib, shu buyurtmaning YANGI ball to'plashini butunlay
        o'tkazib yuboradi (jonli sinovda ikki marta alohida, izolyatsiya
        qilingan testda takrorlanib tasdiqlangan xato).

        Yechim: avval super()ni chaqiramiz (native earn to'liq, o'z
        loyalty.history yozuvlari bilan birga yakunlanadi), FAQAT SHUNDAN
        KEYIN o'zimizning sarflash yozuvimizni yaratamiz — shunda ular bir
        birining tekshiruviga umuman xalaqit bermaydi.
        """
        res = super().confirm_coupon_programs(coupon_data)
        for order in self:
            order._apply_wallet_logic()
        return res

    def _apply_wallet_logic(self):
        """'Cashback' to'lov usuli orqali ishlatilgan summani mijozning
        Odoo Loyalty kartasidan yechadi.

        Cashback TO'PLASH (earn) tomoniga bu modul umuman aralashmaydi —
        u to'liq Odoo'ning o'z Loyalty/pos_loyalty mexanizmi orqali,
        avtomatik davom etadi. Bu metod faqat SARFLASH (spend) tomonini
        boshqaradi. confirm_coupon_programs orqali chaqirilgani uchun
        (order.state hali "paid"ga o'tmagan bo'lishi ham mumkin, lekin bu
        payment_ids allaqachon buyurtmaga bog'langanidan KEYIN chaqiriladi)
        state tekshiruvi ATAYLAB olib tashlandi — faqat wallet_processed
        bayrog'i qayta ishlashning oldini oladi.

        Bu metod g'oyaviy jihatdan POS frontend'dagi tekshiruvlarga
        ishonmaydi — frontend faqat qulaylik/UX uchun (mijozga darhol xato
        ko'rsatish), lekin YAKUNIY, ishonchli hisob-kitob har doim shu
        yerda, serverda amalga oshadi.
        """
        self.ensure_one()
        if self.wallet_processed:
            return

        partner = self.partner_id
        wallet_used = self.wallet_used_amount

        if wallet_used and not partner:
            raise UserError(_(
                "Cashback to'lovi qo'llanilgan buyurtmada mijoz tanlangan bo'lishi shart."
            ))

        if wallet_used and partner:
            partner._wallet_spend(wallet_used, order=self)

        self.write({"wallet_processed": True})

    # E'TIBOR: pos.order uchun _load_pos_data_fields() ATAYLAB override
    # QILINMAYDI — Odoo 19'da pos.order bu mexanizm orqali frontendga
    # OLDINDAN yuklanmaydi; override qilish butun POS ilovasini ishga
    # tushmay qolishiga olib keladi (jonli sinovda topilgan xato).
    # wallet_used_amount POS frontendida kerak emas (u yerda ishlatilgan
    # summa order.payment_ids dan mahalliy hisoblanadi) — faqat backend
    # admin ko'rinishi (pos_order_views.xml) uchun, oddiy read() orqali.
