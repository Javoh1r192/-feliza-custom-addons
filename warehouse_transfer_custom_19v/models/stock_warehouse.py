# -*- coding: utf-8 -*-
from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    allowed_user_ids = fields.Many2many(
        "res.users",
        "stock_warehouse_allowed_users_rel",
        "warehouse_id",
        "user_id",
        string="Ruxsat etilgan foydalanuvchilar",
        help=(
            "Agar belgilansa, faqat shu foydalanuvchilar ushbu omborni ko'ra oladi "
            "va unda ichki o'tkazma (internal transfer) yarata oladi. "
            "Bo'sh qoldirilsa — hamma foydalanuvchi ko'ra oladi."
        ),
    )

    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        # Agar context-da 'all_warehouses' bo'lsa, Record Rule-ni chetlab o'tamiz
        if self.env.context.get("all_warehouses"):
            return super(StockWarehouse, self.sudo())._search(
                domain, offset=offset, limit=limit, order=order, **kwargs
            )
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)