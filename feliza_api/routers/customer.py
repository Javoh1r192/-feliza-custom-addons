from fastapi import APIRouter, Depends, Query

from typing import List

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env

from ..dependencies.api_key import validate_api_key

from ..schemas.request import CreateCustomerRequest, UpdateCustomerRequest
from ..schemas.response import ApiResponse, CustomerResponse, PageResponse

customer_router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
    dependencies=[
        Depends(validate_api_key)
    ]
)


@customer_router.get("", response_model=ApiResponse[PageResponse[CustomerResponse]])
def page(page: int = Query(1, ge=1),
         size: int = Query(10, ge=1, le=100),
         phone: str | None = Query(None),
         fullname: str | None = Query(None),
         externalId: int | None = Query(None),
         env: Environment = Depends(odoo_env)):
    return env["feliza.customers.api.service"].page(page, size, phone, fullname, externalId)

@customer_router.post("/add", response_model=ApiResponse)
def add(req: CreateCustomerRequest, env: Environment = Depends(odoo_env)):
    return env["feliza.customers.api.service"].create(req)

@customer_router.put("/update", response_model=ApiResponse)
def update(req: UpdateCustomerRequest, env: Environment = Depends(odoo_env)):
    return env["feliza.customers.api.service"].update(req)

@customer_router.get("/by-phone", response_model=ApiResponse[CustomerResponse],
                     description="""
                     'User Not found' = User Odoo da mavjud emas.
                     'registrationStatus' = offline . User Do'kondan yoki shunga o'xshash holatda ro'yxatdan o'tkan.
                     'registrationStatus' = 'registered'. User website va odoo da mavjud.
                     Agar responseda externalId qaytarilsa /api/v1/customers/update urlga shu externalId berilishi kerak.
                     Agar customer topilmasa (404) /api/v1/customers/add ga so'rov yuborilib odooda yangi
                     customer yaratiladi - javobida qaytgan (data) qiymat saytda saqlab qo'yiladi.
                     """)
def by_phone(phone: str, env: Environment = Depends(odoo_env)):
    return env["feliza.customers.api.service"].by_phone(phone)

@customer_router.get("/{externalId}/profile", response_model=ApiResponse[CustomerResponse])
def profile(externalId: int, env: Environment = Depends(odoo_env)):
    return env["feliza.customers.api.service"].profile(externalId)