# -*- coding: utf-8 -*-
"""HUJJAT PASPORTI — nakladnoyning tepasidagi ma'lumot bloki

Buyurtmachi talab qilgan ma'lumotlar (5-rasm): hujjat raqami va nomi,
kim yaratdi, kim qabul qildi, qayerdan qayerga, tovar turi va dona
soni, jami summa, yaratilgan sana.

Hammasi hisoblanadigan va SAQLANMAYDIGAN maydonlar — bazaga ustun
qo'shilmaydi, hujjat chop etilganda hisoblanadi.
"""
from odoo import api, fields, models

from .stock_move import feliza_pul, feliza_son


class StockPicking(models.Model):
    _inherit = "stock.picking"

    feliza_sarlavha = fields.Char(
        string="Hujjat turi", compute="_compute_feliza_pasport")
    feliza_qayerdan = fields.Char(
        string="Qayerdan", compute="_compute_feliza_pasport")
    feliza_qayerga = fields.Char(
        string="Qayerga", compute="_compute_feliza_pasport")
    feliza_tur_soni = fields.Integer(
        string="Tovar turi", compute="_compute_feliza_pasport")
    feliza_jami_talab = fields.Float(
        string="Nakladnoy: talab", digits="Product Unit",
        compute="_compute_feliza_pasport")
    feliza_jami_soni = fields.Float(
        string="Nakladnoy: jami dona", digits="Product Unit",
        compute="_compute_feliza_pasport")
    feliza_jami_summa = fields.Monetary(
        string="Jami summa", currency_field="company_currency_id",
        compute="_compute_feliza_pasport")
    feliza_qabul_qildi = fields.Char(
        string="Qabul qildi", compute="_compute_feliza_pasport")
    company_currency_id = fields.Many2one(
        "res.currency", compute="_compute_feliza_pasport")

    feliza_talab_matn = fields.Char(compute="_compute_feliza_pasport")
    feliza_soni_matn = fields.Char(compute="_compute_feliza_pasport")
    feliza_summa_matn = fields.Char(compute="_compute_feliza_pasport")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _feliza_joy_nomi(location):
        """Lokatsiya nomini odam tushunadigan qilib beradi.

        Ombor nomi bo'lsa o'shanisi ko'rsatiladi («Feliza Asosiy»),
        aks holda lokatsiyaning to'liq nomi («Partners/Vendors»).
        """
        if not location:
            return ""
        wh = location.warehouse_id
        if wh:
            return wh.name
        return location.complete_name or location.name or ""

    def _feliza_yonalish(self):
        """Hujjat qayerdan qayerga — ODAM tushunadigan qilib.

        Omborlararo yuk TRANZIT lokatsiyasi orqali yuradi, shuning
        uchun oddiy lokatsiya nomi «Inter Warehouse Transfer» bo'lib
        chiqadi — omborchi uchun bu hech narsa demaydi. Shu sababli
        `warehouse_transfer_custom_19v` moduli qo'yadigan bog'lanishlar
        orqali HAQIQIY jo'natuvchi va qabul qiluvchi ombor topiladi.

        Modul o'rnatilmagan bo'lsa ham ishlaydi: maydonlar bor-yo'qligi
        tekshiriladi, keyin oddiy lokatsiya nomiga qaytiladi.
        """
        self.ensure_one()
        p = self.sudo()
        dan = self._feliza_joy_nomi(p.location_id)
        ga = self._feliza_joy_nomi(p.location_dest_id)
        maydonlar = self._fields

        # kontragent lokatsiyasi bo'lsa — sherik nomi aniqroq
        if p.partner_id:
            if p.location_id.usage in ("supplier", "customer"):
                dan = p.partner_id.name or dan
            if p.location_dest_id.usage in ("supplier", "customer"):
                ga = p.partner_id.name or ga

        # omborlararo bog'lanishlar
        if "inter_wh_delivery_id" in maydonlar and p.inter_wh_delivery_id:
            wh = p.inter_wh_delivery_id.picking_type_id.warehouse_id
            if wh:
                dan = wh.name
        if "source_warehouse_id" in maydonlar and p.source_warehouse_id:
            dan = p.source_warehouse_id.name
        if "destination_warehouse_id" in maydonlar and p.destination_warehouse_id:
            ga = p.destination_warehouse_id.name
        return dan, ga

    @api.depends("move_ids", "state", "picking_type_id", "location_id",
                 "location_dest_id")
    def _compute_feliza_pasport(self):
        turlar = {
            "incoming": "QABUL",
            "outgoing": "JO'NATISH",
            "internal": "ICHKI KO'CHIRISH",
        }
        for picking in self:
            picking.company_currency_id = (
                picking.company_id or self.env.company).currency_id
            picking.feliza_sarlavha = turlar.get(
                picking.picking_type_code, "OMBOR HUJJATI")

            dan, ga = picking._feliza_yonalish()
            picking.feliza_qayerdan = dan
            picking.feliza_qayerga = ga
            sudo_p = picking.sudo()

            qatorlar = picking.move_ids
            picking.feliza_tur_soni = len(qatorlar)
            picking.feliza_jami_talab = sum(qatorlar.mapped("product_uom_qty"))
            picking.feliza_jami_soni = sum(qatorlar.mapped("feliza_soni"))
            picking.feliza_jami_summa = sum(qatorlar.mapped("feliza_summa"))
            picking.feliza_talab_matn = feliza_son(picking.feliza_jami_talab)
            picking.feliza_soni_matn = feliza_son(picking.feliza_jami_soni)
            picking.feliza_summa_matn = feliza_pul(picking.feliza_jami_summa)

            # «Qabul qildi» — hujjatni yakunlagan xodim. Odoo buni alohida
            # saqlamaydi, shuning uchun oxirgi tahrirlovchidan olamiz;
            # hujjat hali yakunlanmagan bo'lsa — bo'sh, qo'lda imzolanadi.
            if picking.state == "done":
                picking.feliza_qabul_qildi = (
                    sudo_p.write_uid.name or sudo_p.user_id.name or "")
            else:
                picking.feliza_qabul_qildi = ""
