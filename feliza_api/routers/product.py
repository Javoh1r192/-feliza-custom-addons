from fastapi import APIRouter, Depends, Query

from typing import List

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env

from ..schemas.response import ApiResponse, OnHandProductResponse, PageResponse, ProductResponse
from ..schemas.request import CheckProductStockRequest

from ..dependencies.api_key import validate_api_key

product_router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[
        Depends(validate_api_key)
    ]
)

@product_router.get("", response_model=ApiResponse[PageResponse[ProductResponse]],
                     description="""
                     Mahsulotlarni ro'yxatini olish uchun (name bo'yicha qidiruv -
                     faqat "saytga chiqarish" belgilangan mahsulotlar chiqadi).

                     externalId/sku/barcode - eski (saytdagi) mahsulot identifikatorini
                     Odoo'ning haqiqiy ID'siga bog'lash uchun: shu parametrlardan biri
                     berilsa, "saytga chiqarish" bayrog'idan qat'i nazar mos mahsulot
                     qidiriladi (bitta natija qaytadi).
                     """)
def page(page: int = Query(1, ge=1),
         size: int = Query(10, ge=1, le=100),
         name: str | None = Query(None),
         externalId: int | None = Query(None),
         sku: str | None = Query(None, description="default_code (mahsulot kodi) bo'yicha aniq qidiruv"),
         barcode: str | None = Query(None, description="barcode bo'yicha aniq qidiruv"),
         env: Environment = Depends(odoo_env)):
    return env["feliza.products.api.service"].page(page, size, name, externalId, sku, barcode)

@product_router.post("/stock", response_model=ApiResponse[List[OnHandProductResponse]])
def stock(req: CheckProductStockRequest, env: Environment = Depends(odoo_env)):
    return env["feliza.products.api.service"].stock(req)