from datetime import datetime

from fastapi import APIRouter, Depends, Query

from typing import List

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env

from ..dependencies.api_key import validate_api_key
from ..schemas.response import ApiResponse

operator_router = APIRouter(
    prefix="/operator",
    tags=["Operator"],
    dependencies=[
        Depends(validate_api_key)
    ]
)


@operator_router.get("/catalog", response_model=ApiResponse,
                      description="1.1 Mahsulot katalogi - model/variant, narx, brend.")
def catalog(page: int = Query(1, ge=1),
            size: int = Query(10, ge=1, le=100),
            sku: str | None = Query(None),
            barcode: str | None = Query(None),
            modelName: str | None = Query(None),
            env: Environment = Depends(odoo_env)):
    return env["feliza.operator.api.service"].catalog(page, size, sku, barcode, modelName)


@operator_router.get("/stock", response_model=ApiResponse,
                      description="1.2 Qoldiq - filial kesimida. Bir nechta variantId birga so'ralishi mumkin.")
def stock(variantId: List[int] = Query(..., min_length=1),
          locationId: int | None = Query(None),
          env: Environment = Depends(odoo_env)):
    return env["feliza.operator.api.service"].stock(variantId, locationId)


@operator_router.get("/sales", response_model=ApiResponse,
                      description="1.3 Sotuvlar (cheklar) - POS va onlayn birlashtirilgan.")
def sales(page: int = Query(1, ge=1),
          size: int = Query(10, ge=1, le=100),
          dateFrom: datetime | None = Query(None),
          dateTo: datetime | None = Query(None),
          locationId: int | None = Query(None),
          env: Environment = Depends(odoo_env)):
    return env["feliza.operator.api.service"].sales(page, size, dateFrom, dateTo, locationId)


@operator_router.get("/receiving", response_model=ApiResponse,
                      description="1.4 Kirim - modelning birinchi kelgan sanasi bilan.")
def receiving(page: int = Query(1, ge=1),
              size: int = Query(10, ge=1, le=100),
              locationId: int | None = Query(None),
              dateFrom: datetime | None = Query(None),
              dateTo: datetime | None = Query(None),
              env: Environment = Depends(odoo_env)):
    return env["feliza.operator.api.service"].receiving(page, size, locationId, dateFrom, dateTo)


@operator_router.get("/customers", response_model=ApiResponse,
                      description="1.5 Mijozlar - xarid tarixi va loyalty balans bilan.")
def customers(page: int = Query(1, ge=1),
              size: int = Query(10, ge=1, le=100),
              phone: str | None = Query(None),
              env: Environment = Depends(odoo_env)):
    return env["feliza.operator.api.service"].customers(page, size, phone)


@operator_router.get("/transfers", response_model=ApiResponse,
                      description="1.6 Do'konlararo ko'chirish.")
def transfers(page: int = Query(1, ge=1),
              size: int = Query(10, ge=1, le=100),
              dateFrom: datetime | None = Query(None),
              dateTo: datetime | None = Query(None),
              env: Environment = Depends(odoo_env)):
    return env["feliza.operator.api.service"].transfers(page, size, dateFrom, dateTo)
