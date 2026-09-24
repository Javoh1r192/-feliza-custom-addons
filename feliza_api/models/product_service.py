from odoo import models
from fastapi import HTTPException


from ..schemas.response import PageResponse

class ProductsApiService(models.AbstractModel):
    _name = "feliza.products.api.service"
    _description = "Products API Service"

    def page(self, page, size, name=None, externalId=None, sku=None, barcode=None):
        # externalId/sku/barcode - aniq bitta mahsulotni topish uchun
        # (masalan eski tashqi ID'ni Odoo ID'ga bog'lash), shuning uchun
        # "saytga chiqarish" bayrog'idan qat'i nazar qidiradi. `name` esa
        # sayt katalogini ko'rish uchun - faqat nashr qilingan mahsulotlar.
        if externalId:
            domain = [("id", "=", externalId)]
        elif sku:
            domain = [("default_code", "=", sku)]
        elif barcode:
            domain = [("barcode", "=", barcode)]
        else:
            domain = [("product_tmpl_id.x_publish_web", "=", True)]
            if name:
                domain.append(("name", "ilike", name))

        total_elements = self.env["product.product"].sudo().search_count(domain)
        if total_elements == 0:
            return {"success": True, "message": "success", "data": PageResponse.empty(page, size)}

        products = self.env["product.product"].sudo().search(
            domain,
            offset=(page - 1) * size,
            limit=size,
            order="id desc",
        )

        content = [
            {
                "externalId": product.id,
                "price": product.list_price,
                "name": product.display_name,
                "quantity": product.virtual_available
            }
            for product in products
        ]

        return {
            "success": True,
            "message": "success",
            "data": PageResponse.of(content, page, size, total_elements)
        }

    def stock(self, req):
        warehouse = self.env["stock.warehouse"].sudo().search([
            ("name", "=", "Online Ombor")
        ], limit=1)
        if not warehouse:
            raise HTTPException(status_code=404, detail="Online Ombor not found")

        # "Online Ombor" texnik ombor, filial emas - filial qoldig'ini
        # chiqarayotganda bu qatnashmaydi.
        branch_warehouses = self.env["stock.warehouse"].sudo().search([
            ("id", "!=", warehouse.id)
        ])

        products = (
            self.env["product.product"]
            .sudo()
            .with_context(warehouse_id=warehouse.id)
            .search([
                ("id", "in", req.externalIds)
            ])
        )

        result = []

        for product in products:
            branches = [
                {
                    "warehouseId": branch.id,
                    "name": branch.name,
                    # free_qty = mavjud - rezervlangan (sotib bo'ladigan qoldiq)
                    "quantity": product.with_context(warehouse_id=branch.id).free_qty,
                }
                for branch in branch_warehouses
            ]

            result.append({
                "externalId": product.id,
                "onHand": product.virtual_available,
                "branches": branches,
            })

        return {"success": True, "message": "success", "data": result}