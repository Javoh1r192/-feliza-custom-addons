from fastapi import APIRouter, Depends

from typing import List

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env

from ..dependencies.api_key import validate_api_key

from ..schemas.response import ApiResponse, CashbackResponse

cashback_router = APIRouter(
    prefix="/cashback",
    tags=["Cashback"],
    dependencies=[
        Depends(validate_api_key)
    ]
)


@cashback_router.get("/{customerExternalId}",  response_model=ApiResponse)
def cashback(customerExternalId: int, env: Environment = Depends(odoo_env)):
    return env["feliza.cashback.api.service"].cashback(customerExternalId)

@cashback_router.get("/{customerExternalId}/history",  response_model=ApiResponse[List[CashbackResponse]])
def history(customerExternalId: int, env: Environment = Depends(odoo_env)):
    return env["feliza.cashback.api.service"].history(customerExternalId)