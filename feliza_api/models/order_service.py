from odoo import models
from typing import List

from fastapi import HTTPException

import logging
from operator import itemgetter

_logger = logging.getLogger(__name__)



class OrderApiService(models.AbstractModel):
    _name = "feliza.order.api.service"
    _description = "Order API Service"

    def get_one_order(self, webOrderId):
        sale_orders = self.env["sale.order"].sudo().search([("web_order_id", "=", webOrderId)])

        pos_orders = self.env["pos.order"].sudo().search([("web_order_id", "=", webOrderId)])

        if not sale_orders and not pos_orders:
            raise HTTPException(status_code=404, detail="Order not found")

        if sale_orders:
            data = self.build_sale_order(sale_orders)
            return {"success": True, "message": "success", "data": data}
        else:
            data = self.build_pos_order(pos_orders)
            return {"success": True, "message": "success", "data": data}


    def orders(self, customerExternalId):
        sale_orders = self.env["sale.order"].sudo().search([
            ("partner_id", "=", customerExternalId),
            ("web_order_id", '!=', False)
        ])

        pos_orders = self.env["pos.order"].sudo().search([
            ("partner_id", "=", customerExternalId),
            ("web_order_id", "!=", False)
        ])

        result = []
        if not sale_orders and not pos_orders:
            return {"success": True, "message": "success", "data": result}

        for order in sale_orders:
            result.append(self.build_sale_order(order))

        for order in pos_orders:
            result.append(self.build_pos_order(order))

        result.sort(key=itemgetter("date"), reverse=True,)

        return {"success": True, "message": "success", "data": result}

    def build_sale_order(self, order):
        products = []
        rewards = []

        for line in order.order_line:
            if line.reward_id:
                rewards.append({
                    "type": line.reward_id.reward_type,
                    "name": line.name,
                    "amount": abs(line.price_subtotal),
                })
            else:
                products.append({
                    "externalId": line.product_id.id,
                    "name": line.product_id.display_name,
                    "quantity": line.product_uom_qty,
                    "price": line.price_unit,
                    "discount_percent": line.discount,
                    "discount_amount": (line.price_unit * line.product_uom_qty * line.discount / 100)
                })

        return {
            "webOrderId": order.web_order_id,
            "number": order.name,
            "status": order.state,
            "date": order.date_order,
            "amount": order.amount_total,
            "tags": order.tag_ids.mapped("name"),
            "orderSource": "Online",
            "products": products,
            "rewards": rewards,
        }

    def build_pos_order(self, order):
        products = []
        rewards = []

        for line in order.lines:
            if line.reward_id:
                rewards.append({
                    "type": line.reward_id.reward_type,
                    "name": line.name,
                    "amount": abs(line.price_subtotal),
                })
            else:
                products.append({
                    "externalId": line.product_id.id,
                    "name": line.product_id.display_name,
                    "quantity": line.qty,
                    "price": line.price_unit,
                    "discount_percent": line.discount,
                    "discount_amount": (line.price_unit * line.qty * line.discount / 100)
                })

        return {
            "webOrderId": order.web_order_id,
            "number": order.name,
            "status": order.state,
            "date": order.date_order,
            "amount": order.amount_total,
            "tags": [],
            "orderSource": "Offline",
            "products": products,
            "rewards": rewards,
        }

    def cancel(self, webOrderId):
        sale_order = self.env['sale.order'].sudo().search([("web_order_id", "=", webOrderId)])
        if not sale_order:
            raise HTTPException(status_code=404, detail="Order not found")

        for picking in sale_order.picking_ids:
            if picking.state not in ("done", "cancel"):
                picking.action_cancel()

        sale_order.action_cancel()
        return {"success": True, "message": "success", "data": "cancelled"}

    def create(self, req):
        customer = self.env['res.partner'].sudo().browse(req.customerExternalId).exists()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        sale_order = self.env['sale.order'].sudo().search_read(
            domain=[('web_order_id', '=', req.webOrderId)],
            fields=['id']
        )
        if sale_order:
            raise HTTPException(status_code=409, detail="Order with this webOrderId already exists")

        online_warehouse = self.env["stock.warehouse"].sudo().search([
            ("name", "=", "Online Ombor")
        ], limit=1)
        if not online_warehouse:
            raise HTTPException(status_code=404, detail="Online Warehouse not found")

        admin = self.env.ref("base.user_admin")

        env = self.env(user=admin.id)

        order_vals = {
            "partner_id": customer.id,
            "client_order_ref": req.orderNumber,
            "order_number": req.orderNumber,
            "web_order_id": req.webOrderId,
            "delivery_address": req.deliveryAddress,
            "delivery_method": req.deliveryMethod,
            "delivery_fee": req.deliveryFee,
            "payment_method": req.paymentMethod,
            "payment_status": req.paymentStatus,
            "payment_txn_id": req.paymentTxnId,
            "web_order_created": req.createdAt,
            "warehouse_id": online_warehouse.id,
        }

        website_tag = env["crm.tag"].sudo().search_read(
            domain=[("name", "=", "Website")],
            fields=['id'], limit=1
        )
        if website_tag:
            order_vals['tag_ids'] = [(6, 0, [website_tag[0]['id']])]

        order = env["sale.order"].sudo().create(order_vals)

        for line in req.lines:

            product = self.env["product.product"].sudo().browse(line.productExternalId).exists()

            if not product:
                raise HTTPException(status_code=404, detail=f"Product not found: {line.productExternalId}")

            self.env["sale.order.line"].sudo().create({
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": line.qty,
                "price_unit": line.unitPrice,
                "discount": line.discount,
                "name": product.name,
            })

        if req.cashbackUsed > 0:
            program = self.env["loyalty.program"].sudo().search([
                ("name", "=", "Cashback"),
                ("program_type", "=", "loyalty"),
            ], limit=1)

            if not program:
                raise HTTPException(status_code=404, detail="Cashback program not found.")

            reward = program.reward_ids[:1]

            if not reward:
                raise HTTPException(status_code=404, detail="Cashback reward not found.")

            card = self.env["loyalty.card"].sudo().search([
                ("partner_id", "=", customer.id),
                ("program_id", "=", program.id),
            ], limit=1)

            if not card:
                raise HTTPException(status_code=404, detail="Cashback card not found.")

            if card.points < req.cashbackUsed:
                raise HTTPException(status_code=400, detail="Not enough cashback.")

            order.applied_coupon_ids |= card

            order = order.with_context(cashback_used_points=req.cashbackUsed)

            result = order._apply_program_reward(reward, card)

            if result.get("error"):
                raise HTTPException(status_code=400, detail=f"{result['error']}")

            order._update_programs_and_rewards()

        order.action_confirm()

        return {
            "success": True,
            "message": "Order created successfully.",
            "data": {
                "webOrderId": req.webOrderId,
                "name": order.name,
            }
        }