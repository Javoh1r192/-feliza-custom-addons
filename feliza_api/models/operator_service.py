from odoo import models

from .feliza_webhook_client import to_feliza_datetime
from ..schemas.response import PageResponse


class OperatorApiService(models.AbstractModel):
    """AI operator (mijozlarga savol-javob beruvchi tizim) uchun o'qish uchun
    API. Feliza backendning o'z shartnomasidan (routers/customer.py,
    routers/product.py va h.k. - camelCase, "externalId") ATAYLAB alohida
    ushlanadi - bu yerdagi iste'molchi boshqa, maydon nomlari ham spec'da
    berilganidek snake_case."""

    _name = "feliza.operator.api.service"
    _description = "AI Operator API Service"

    # ------------------------------------------------------------------ #
    # 1.1 Mahsulot katalogi
    # ------------------------------------------------------------------ #

    def catalog(self, page, size, sku=None, barcode=None, modelName=None):
        # sale_ok=False - loyalty/discount dasturlari yaratadigan "soxta"
        # mahsulotlar (masalan "15% chegirma"), haqiqiy katalog emas.
        domain = [("sale_ok", "=", True)]
        if sku:
            domain.append(("default_code", "=", sku))
        if barcode:
            domain.append(("barcode", "=", barcode))
        if modelName:
            domain.append(("product_tmpl_id.name", "ilike", modelName))

        Product = self.env["product.product"].sudo()
        total_elements = Product.search_count(domain)
        if total_elements == 0:
            return {"success": True, "message": "success", "data": PageResponse.empty(page, size)}

        products = Product.search(domain, offset=(page - 1) * size, limit=size, order="id desc")
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")

        content = [self._build_catalog_item(p, base_url) for p in products]

        return {
            "success": True,
            "message": "success",
            "data": PageResponse.of(content, page, size, total_elements),
        }

    def _build_catalog_item(self, product, base_url):
        size_value = None
        color_value = None
        for ptav in product.product_template_attribute_value_ids:
            if ptav.attribute_id.is_size:
                size_value = ptav.product_attribute_value_id.name
            else:
                # Hozircha faqat 2 ta atribut haqiqatda ishlatiladi (o'lcham +
                # rang) - shuning uchun "o'lcham bo'lmagan birinchisi" rangga
                # tenglashtiriladi. ponytail: ko'proq atribut ishlatila
                # boshlasa, shu yerga "is_color" belgisi qo'shish kerak
                # bo'ladi (feliza_size_split'dagi is_size kabi).
                color_value = color_value or ptav.product_attribute_value_id.name

        image_url = None
        if product.image_1920:
            image_url = f"{base_url}/web/image/product.product/{product.id}/image_1920"

        return {
            "sku": product.default_code or None,
            "barcode": product.barcode or None,
            "model_name": product.product_tmpl_id.name,
            "variant_id": product.id,
            "size": size_value,
            "color": color_value,
            "category": product.categ_id.complete_name or None,
            "brand": product.product_tmpl_id.x_brand or None,
            "retail_price": product.lst_price,
            "cost_price": product.standard_price,
            "image_url": image_url,
        }

    # ------------------------------------------------------------------ #
    # 1.2 Qoldiq - filial kesimida
    # ------------------------------------------------------------------ #

    def stock(self, variant_ids, location_id=None):
        domain = [
            ("product_id", "in", variant_ids),
            ("location_id.usage", "=", "internal"),
        ]
        if location_id:
            domain.append(("location_id", "=", location_id))

        # Bevosita stock.quant'ni o'qiymiz (free_qty kabi context-based
        # hisoblashsiz) - AI operator javobi 2 sekunddan tez bo'lishi kerak.
        quants = self.env["stock.quant"].sudo().search(domain)

        content = [
            {
                "variant_id": q.product_id.id,
                "location_id": q.location_id.id,
                "location_name": q.location_id.warehouse_id.name or q.location_id.display_name,
                "quantity": q.quantity,
                "updated_at": to_feliza_datetime(q.write_date),
            }
            for q in quants
        ]
        return {"success": True, "message": "success", "data": content}

    # ------------------------------------------------------------------ #
    # 1.3 Sotuvlar (cheklar)
    # ------------------------------------------------------------------ #

    def sales(self, page, size, date_from=None, date_to=None, location_id=None):
        # ponytail: filtrsiz (butun tarix) so'ralsa sekinlashadi (~2.4s
        # 3400+ chekda) - amalda dateFrom/dateTo har doim berilishi kerak
        # (masalan "bugungi cheklar"). Filtrlangan holatda <30ms.
        pos_domain = [("state", "in", ["paid", "done", "invoiced"])]
        sale_domain = [("state", "=", "sale")]
        if date_from:
            pos_domain.append(("date_order", ">=", date_from))
            sale_domain.append(("date_order", ">=", date_from))
        if date_to:
            pos_domain.append(("date_order", "<=", date_to))
            sale_domain.append(("date_order", "<=", date_to))
        if location_id:
            pos_domain.append(("session_id.config_id.warehouse_id", "=", location_id))
            sale_domain.append(("warehouse_id", "=", location_id))

        PosOrder = self.env["pos.order"].sudo()
        SaleOrder = self.env["sale.order"].sudo()

        # ponytail: ikkala manbani birlashtirib sahifalashning to'g'ri yo'li
        # SQL UNION bo'lardi, lekin hozircha hajm katta emas - avval POS
        # (asosiy, do'kon savdosi), keyin online cheklar, Python darajasida
        # kesib olinadi. Sekinlashsa shu yerni SQL'ga o'tkazish kerak.
        pos_orders = PosOrder.search(pos_domain, order="date_order desc")
        sale_orders = SaleOrder.search(sale_domain, order="date_order desc")

        all_receipts = sorted(
            [self._build_pos_receipt(o) for o in pos_orders]
            + [self._build_sale_receipt(o) for o in sale_orders],
            key=lambda r: r["datetime"] or "",
            reverse=True,
        )

        total_elements = len(all_receipts)
        if total_elements == 0:
            return {"success": True, "message": "success", "data": PageResponse.empty(page, size)}

        start = (page - 1) * size
        content = all_receipts[start:start + size]

        return {
            "success": True,
            "message": "success",
            "data": PageResponse.of(content, page, size, total_elements),
        }

    def _build_pos_receipt(self, order):
        location = order.session_id.config_id.warehouse_id
        lines = order.lines.filtered(lambda l: not l.is_reward_line)
        salesperson = order.salesperson_emp_id.name or None

        return {
            "order_id": order.id,
            "receipt_number": order.pos_reference or order.name,
            "source": "Offline",
            "datetime": to_feliza_datetime(order.date_order),
            "location_id": location.id or None,
            "location_name": location.name or None,
            "total_amount": order.amount_total,
            "discount_amount": sum(
                (l.price_unit * l.qty * l.discount / 100) for l in lines
            ),
            "payment_method": ", ".join(order.payment_ids.mapped("payment_method_id.name")) or None,
            "cashier": (order.employee_id.name or order.user_id.name) or None,
            "customer_phone": order.partner_id.phone or None,
            "is_return": order.is_refund,
            "lines": [
                {
                    "variant_id": l.product_id.id,
                    "qty": l.qty,
                    "unit_price": l.price_unit,
                    "discount": l.discount,
                    "line_total": l.price_subtotal_incl,
                    "cost_price": l.product_id.standard_price,
                    "salesperson": salesperson,
                }
                for l in lines
            ],
        }

    def _build_sale_receipt(self, order):
        lines = order.order_line.filtered(lambda l: not l.reward_id)

        return {
            "order_id": order.id,
            "receipt_number": order.name,
            "source": "Online",
            "datetime": to_feliza_datetime(order.date_order),
            "location_id": order.warehouse_id.id or None,
            "location_name": order.warehouse_id.name or None,
            "total_amount": order.amount_total,
            "discount_amount": sum(
                (l.price_unit * l.product_uom_qty * l.discount / 100) for l in lines
            ),
            "payment_method": order.payment_method or None,
            # Online buyurtmada kassir/sotuvchi tushunchasi yo'q.
            "cashier": None,
            "customer_phone": order.partner_id.phone or None,
            "is_return": order.state == "cancel",
            "lines": [
                {
                    "variant_id": l.product_id.id,
                    "qty": l.product_uom_qty,
                    "unit_price": l.price_unit,
                    "discount": l.discount,
                    "line_total": l.price_subtotal,
                    "cost_price": l.product_id.standard_price,
                    "salesperson": None,
                }
                for l in lines
            ],
        }

    # ------------------------------------------------------------------ #
    # 1.4 Kirim
    # ------------------------------------------------------------------ #

    def receiving(self, page, size, location_id=None, date_from=None, date_to=None):
        domain = [
            ("picking_id.picking_type_id.code", "=", "incoming"),
            ("state", "=", "done"),
        ]
        if location_id:
            domain.append(("location_dest_id", "=", location_id))
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))

        MoveLine = self.env["stock.move.line"].sudo()
        total_elements = MoveLine.search_count(domain)
        if total_elements == 0:
            return {"success": True, "message": "success", "data": PageResponse.empty(page, size)}

        lines = MoveLine.search(domain, offset=(page - 1) * size, limit=size, order="date desc")

        # Har bir mahsulot uchun "modelning birinchi kelgan sanasi"ni
        # sahifadagi noyob mahsulotlar bo'yicha bittalab (N+1 emas) hisoblaymiz.
        templates = lines.mapped("product_id.product_tmpl_id")
        first_received_by_tmpl = {}
        if templates:
            first_rows = self.env["stock.move.line"].sudo().read_group(
                domain=[
                    ("product_id.product_tmpl_id", "in", templates.ids),
                    ("picking_id.picking_type_id.code", "=", "incoming"),
                    ("state", "=", "done"),
                ],
                fields=["date:min"],
                groupby=["product_id"],
            )
            product_first = {row["product_id"][0]: row["date"] for row in first_rows if row.get("date")}
            for product in lines.mapped("product_id"):
                tmpl_id = product.product_tmpl_id.id
                first_received_by_tmpl[tmpl_id] = min(
                    [
                        product_first[p.id]
                        for p in product.product_tmpl_id.product_variant_ids
                        if p.id in product_first
                    ],
                    default=None,
                )

        content = []
        for line in lines:
            purchase_line = line.move_id.purchase_line_id
            content.append({
                "variant_id": line.product_id.id,
                "location_id": line.location_dest_id.id,
                "qty": line.quantity,
                "received_at": to_feliza_datetime(line.date),
                "supply_price": purchase_line.price_unit if purchase_line else None,
                "first_received_at": to_feliza_datetime(
                    first_received_by_tmpl.get(line.product_id.product_tmpl_id.id)
                ),
            })

        return {
            "success": True,
            "message": "success",
            "data": PageResponse.of(content, page, size, total_elements),
        }

    # ------------------------------------------------------------------ #
    # 1.5 Mijozlar
    # ------------------------------------------------------------------ #

    def customers(self, page, size, phone=None):
        domain = [("phone", "!=", False)]
        if phone:
            domain.append(("phone", "ilike", phone))

        Partner = self.env["res.partner"].sudo()
        total_elements = Partner.search_count(domain)
        if total_elements == 0:
            return {"success": True, "message": "success", "data": PageResponse.empty(page, size)}

        partners = Partner.search(domain, offset=(page - 1) * size, limit=size, order="id desc")

        content = [self._build_customer_item(p) for p in partners]

        return {
            "success": True,
            "message": "success",
            "data": PageResponse.of(content, page, size, total_elements),
        }

    def _build_customer_item(self, partner):
        # ponytail: har mijoz uchun to'g'ridan-to'g'ri qidiruv - sahifa
        # hajmi kichik (<=100) bo'lgani uchun yetarli. Sekinlashsa, SQL
        # agregatsiyaga o'tkazish kerak.
        pos_orders = self.env["pos.order"].sudo().search([
            ("partner_id", "=", partner.id),
            ("state", "in", ["paid", "done", "invoiced"]),
        ])
        sale_orders = self.env["sale.order"].sudo().search([
            ("partner_id", "=", partner.id),
            ("state", "=", "sale"),
        ])

        dates = pos_orders.mapped("date_order") + sale_orders.mapped("date_order")
        cards = self.env["loyalty.card"].sudo().search([("partner_id", "=", partner.id)])

        return {
            "id": partner.id,
            "phone": partner.phone or None,
            "name": partner.name or None,
            "gender": partner.x_gender or None,
            "birth_date": partner.birthdate.isoformat() if partner.birthdate else None,
            "first_purchase_at": to_feliza_datetime(min(dates)) if dates else None,
            "last_purchase_at": to_feliza_datetime(max(dates)) if dates else None,
            "total_spent": sum(pos_orders.mapped("amount_total")) + sum(sale_orders.mapped("amount_total")),
            "purchase_count": len(pos_orders) + len(sale_orders),
            "loyalty_balance": sum(cards.mapped("points")),
        }

    # ------------------------------------------------------------------ #
    # 1.6 Do'konlararo ko'chirish
    # ------------------------------------------------------------------ #

    def transfers(self, page, size, date_from=None, date_to=None):
        # warehouse_transfer_custom_19v: bitta jismoniy ko'chirish DELIVERY
        # hujjatida (destination_warehouse_id bilan) to'liq ifodalanadi -
        # bog'liq Receipt'ni alohida qo'shsak, miqdor ikki baravar bo'lib
        # qoladi.
        domain = [
            ("picking_type_code", "=", "outgoing"),
            ("destination_warehouse_id", "!=", False),
        ]
        if date_from:
            domain.append(("create_date", ">=", date_from))
        if date_to:
            domain.append(("create_date", "<=", date_to))

        Picking = self.env["stock.picking"].sudo()
        pickings = Picking.search(domain, order="create_date desc")

        all_lines = []
        for picking in pickings:
            from_name = picking.warehouse_id.name or picking.location_id.display_name
            to_name = picking.destination_warehouse_id.name
            for line in picking.move_line_ids:
                all_lines.append({
                    "from_location": from_name,
                    "to_location": to_name,
                    "variant_id": line.product_id.id,
                    "qty": line.quantity,
                    "status": picking.state,
                    "created_at": to_feliza_datetime(picking.create_date),
                    "completed_at": to_feliza_datetime(picking.date_done),
                })

        total_elements = len(all_lines)
        if total_elements == 0:
            return {"success": True, "message": "success", "data": PageResponse.empty(page, size)}

        start = (page - 1) * size
        content = all_lines[start:start + size]

        return {
            "success": True,
            "message": "success",
            "data": PageResponse.of(content, page, size, total_elements),
        }
