# -*- coding: utf-8 -*-
"""QABUL QILUVCHI OMBOR UCHUN KO'RINADIGAN OPERATSIYA TURLARI

NEGA KERAK
----------
«Personal Warehouse Only dostup» qoidasi operatsiya turini (stock.picking.type)
faqat o'z ombori bo'yicha ochadi. Omborlararo yukda esa hujjat
JO'NATUVCHI omborning operatsiya turida yaratiladi («Asosi: Доставка»).

Hujjatning o'zini ko'rish qoidasini tuzatganimizdan keyin do'kon boshlig'i
«Asosi/OUT/00026» ni ro'yxatda ko'radi, lekin uni OCHOLMAYDI: forma
`picking_type_id` maydonini o'qishga urinadi va yangi «Ошибка доступа»
chiqadi. Ya'ni bitta xatoni tuzatib, o'rniga boshqasini qo'ygan bo'lardik.

Shu maydon aynan shuni yopadi: xodimga FAQAT o'ziga yuk jo'natgan
omborlarning operatsiya turlari ochiladi. Boshqa omborlarniki avvalgidek
yopiq qoladi — «Ombor ko'rinishi» sahifasida ortiqcha kartochka chiqmaydi.

NEGA XOM SQL
------------
Maydon yozuv qoidasi (ir.rule) ichida o'qiladi. Agar bu yerda ORM orqali
`stock.picking` qidirsak, u o'z navbatida `stock.picking.type` qoidasini
qayta chaqirib, cheksiz aylanma hosil bo'lardi. Xom so'rov qoidalarni
umuman chaqirmaydi — shuning uchun xavfsiz.
"""
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    interwh_visible_picking_type_ids = fields.Many2many(
        "stock.picking.type",
        string="Omborlararo: ko'rinadigan operatsiya turlari",
        compute="_compute_interwh_visible_picking_type_ids",
        help="Shu xodimning omboriga yuk jo'natgan omborlarning operatsiya "
             "turlari. Faqat hujjatni ocha olish uchun ishlatiladi.")

    def _compute_interwh_visible_picking_type_ids(self):
        # kutilayotgan yozuvlar bazaga tushsin — xom so'rov ularni
        # ko'rmasligi mumkin
        self.env["stock.picking"].flush_model(
            ["picking_type_id", "destination_warehouse_id"])

        for user in self:
            if not user.id:                  # saqlanmagan yozuv (NewId)
                user.interwh_visible_picking_type_ids = False
                continue
            self.env.cr.execute("""
                SELECT DISTINCT p.picking_type_id
                  FROM stock_picking p
                  JOIN stock_warehouse_allowed_users_rel r
                    ON r.warehouse_id = p.destination_warehouse_id
                 WHERE r.user_id = %s
                   AND p.picking_type_id IS NOT NULL
            """, (user.id,))
            user.interwh_visible_picking_type_ids = [
                row[0] for row in self.env.cr.fetchall()]
