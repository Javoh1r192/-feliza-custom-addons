# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class StockWarehouseMonthlyReport(models.Model):
    """
    OMBOR HISOBOTI
    ==============
    Har bir ombor (filial) va mahsulot bo'yicha, OYLIK kesimda:
      - Kirim: tasdiqlangan Purchase Order orqali kelgan miqdor
               + (agar mavjud bo'lsa) omborlar aro transferdan qabul
               qilingan miqdor + "Return" orqali qaytib kelgan miqdor
      - Chiqim: mijozga sotuv (Sales VA POS) orqali chiqqan miqdor
               + (agar mavjud bo'lsa) omborlar aro transferga
               yuborilgan miqdor
      - Qoldiq: oy oxiridagi YIG'MA (running) balans
      - Qoldiq qiymati: qoldiq miqdori x mahsulotning HOZIRGI tannarxi

    MUHIM CHEKLOV: Odoo 19'da stock.valuation.layer modeli olib
    tashlangan, shuning uchun "har oyning o'zidagi haqiqiy tannarxi"ni
    ishonchli tarzda saqlab bo'lmaydi. "Qoldiq qiymati" mahsulotning
    JORIY tannarxi asosida hisoblanadi.

    MUSTAQILLIK: Bu modul HECH QANDAY boshqa maxsus modulga bog'liq
    emas - faqat "stock", "stock_account", "purchase" (standart Odoo
    modullari). Agar "warehouse_transfer_custom_19v" moduli o'rnatilgan
    bo'lsa, u qo'shgan stock.picking.inter_wh_delivery_id va
    destination_warehouse_id maydonlaridan (agar bazada mavjud bo'lsa)
    "bonus" sifatida foydalaniladi - transfer harakatlari ham
    kirim/chiqimga qo'shiladi. Aks holda bu ustunlar shunchaki 0 bo'lib
    qoladi va hisobot faqat Purchase/Sales/POS asosida to'g'ri ishlayveradi.
    """

    _name = "stock.warehouse.monthly.report"
    _description = "Ombor hisoboti (oylik kirim/chiqim/qoldiq)"
    _auto = False
    _order = "date desc, warehouse_id, product_id"

    warehouse_id = fields.Many2one("stock.warehouse", string="Ombor", readonly=True)
    product_id = fields.Many2one("product.product", string="Mahsulot", readonly=True)
    date = fields.Date(string="Oy", readonly=True)
    kirim_qty = fields.Float(string="Kirim", readonly=True, group_operator="sum")
    chiqim_qty = fields.Float(string="Chiqim", readonly=True, group_operator="sum")
    qoldiq_qty = fields.Float(string="Qoldiq", readonly=True, group_operator="sum")
    qoldiq_value = fields.Float(
        string="Qoldiq qiymati",
        readonly=True,
        group_operator="sum",
        help=(
            "Qoldiq miqdori x mahsulotning HOZIRGI tannarxi (SQL "
            "view'ning o'zida hisoblanadi - har doim joriy narxni "
            "aks ettiradi)."
        ),
    )
    company_id = fields.Many2one("res.company", string="Kompaniya", readonly=True)

    def _table_has_columns(self, table, columns):
        """Berilgan jadvalda berilgan ustunlar mavjudligini tekshiradi -
        boshqa (ixtiyoriy) modul o'rnatilganligini aniqlash uchun."""
        self.env.cr.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND column_name = ANY(%s)
            """,
            (table, columns),
        )
        found = {row[0] for row in self.env.cr.fetchall()}
        return set(columns) <= found

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        has_transfer_fields = self._table_has_columns(
            "stock_picking", ["inter_wh_delivery_id", "destination_warehouse_id"]
        )
        if has_transfer_fields:
            transfer_kirim_expr = (
                "CASE WHEN spt.code = 'incoming' AND sp.inter_wh_delivery_id "
                "IS NOT NULL THEN sm.quantity ELSE 0 END"
            )
            transfer_chiqim_expr = (
                "CASE WHEN spt.code = 'outgoing' AND sp.destination_warehouse_id "
                "IS NOT NULL THEN sm.quantity ELSE 0 END"
            )
        else:
            # "warehouse_transfer_custom_19v" moduli o'rnatilmagan -
            # transfer ustunlari shunchaki 0, hisobot xatosiz ishlayveradi.
            transfer_kirim_expr = "0"
            transfer_chiqim_expr = "0"

        query = """
            CREATE OR REPLACE VIEW {table} AS (
                WITH flows AS (
                    SELECT
                        spt.warehouse_id                           AS warehouse_id,
                        sm.product_id                              AS product_id,
                        date_trunc('month', sm.date)::date         AS month,
                        sp.company_id                              AS company_id,
                        CASE WHEN spt.code = 'incoming'
                                  AND sm.purchase_line_id IS NOT NULL
                             THEN sm.quantity ELSE 0 END            AS purchase_kirim,
                        ({transfer_kirim_expr})                    AS transfer_kirim,
                        CASE WHEN sm.origin_returned_move_id IS NOT NULL
                             THEN sm.quantity ELSE 0 END            AS return_kirim,
                        CASE WHEN spt.code = 'outgoing'
                                  AND loc_dest.usage = 'customer'
                             THEN sm.quantity ELSE 0 END            AS sale_chiqim,
                        ({transfer_chiqim_expr})                   AS transfer_chiqim
                    FROM stock_move sm
                    JOIN stock_picking sp ON sp.id = sm.picking_id
                    JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                    JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                    WHERE sm.state = 'done'
                      AND spt.warehouse_id IS NOT NULL
                      AND sm.product_id IS NOT NULL
                ),
                monthly AS (
                    SELECT
                        warehouse_id,
                        product_id,
                        month,
                        company_id,
                        SUM(purchase_kirim + transfer_kirim + return_kirim) AS kirim_qty,
                        SUM(sale_chiqim + transfer_chiqim)                  AS chiqim_qty
                    FROM flows
                    GROUP BY warehouse_id, product_id, month, company_id
                ),
                balances AS (
                    SELECT
                        warehouse_id,
                        product_id,
                        month,
                        company_id,
                        kirim_qty,
                        chiqim_qty,
                        SUM(kirim_qty - chiqim_qty) OVER (
                            PARTITION BY warehouse_id, product_id ORDER BY month
                        ) AS qoldiq_qty
                    FROM monthly
                )
                SELECT
                    row_number() OVER ()                            AS id,
                    b.warehouse_id                                  AS warehouse_id,
                    b.product_id                                    AS product_id,
                    b.month                                         AS date,
                    b.company_id                                    AS company_id,
                    b.kirim_qty                                     AS kirim_qty,
                    b.chiqim_qty                                    AS chiqim_qty,
                    b.qoldiq_qty                                    AS qoldiq_qty,
                    b.qoldiq_qty * COALESCE(
                        (
                            SELECT value::numeric
                            FROM jsonb_each_text(COALESCE(pp.standard_price, '{{}}'::jsonb))
                            LIMIT 1
                        ),
                        0.0
                    )                                                AS qoldiq_value
                FROM balances b
                JOIN product_product pp ON pp.id = b.product_id
            )
        """.format(
            table=self._table,
            transfer_kirim_expr=transfer_kirim_expr,
            transfer_chiqim_expr=transfer_chiqim_expr,
        )

        self.env.cr.execute(query)
