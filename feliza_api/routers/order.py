from fastapi import APIRouter, Depends

from typing import List

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env

from ..dependencies.api_key import validate_api_key

from ..schemas.response import ApiResponse, CreateOrderResponse, OrderResponse
from ..schemas.request import CreateOrderRequest

order_router = APIRouter(
    prefix="/orders",
    tags=["Order"],
    dependencies=[
        Depends(validate_api_key)
    ]
)


@order_router.get("/{customerExternalId}/customer",  response_model=ApiResponse[List[OrderResponse]])
def orders(customerExternalId: int, env: Environment = Depends(odoo_env)):
    return env["feliza.order.api.service"].orders(customerExternalId)

@order_router.get("/{webOrderId}",  response_model=ApiResponse[OrderResponse])
def get_one_order(webOrderId: str, env: Environment = Depends(odoo_env)):
    return env["feliza.order.api.service"].get_one_order(webOrderId)

@order_router.post("/create", response_model=ApiResponse[CreateOrderResponse],
                   description="""
                   deliveryMethod = (courier, pickup, branch_pickup),
                   paymentMethod = (payme, click, uzum, cod),
                   paymentType = (pending, paid, failed, cancelled),
                   """)
def create(req: CreateOrderRequest, env: Environment = Depends(odoo_env)):
    return env["feliza.order.api.service"].create(req)

@order_router.post("/{webOrderId}/cancel", response_model=ApiResponse)
def cancel(webOrderId: str, env: Environment = Depends(odoo_env)):
    return env["feliza.order.api.service"].cancel(webOrderId)