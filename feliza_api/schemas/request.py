from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal
from typing import List

#Customer endpoint

class CreateCustomerRequest(BaseModel):
    fullname: str = Field()
    phone: str = Field(pattern=r"^\+998\d{9}$", json_schema_extra={"example": "+998901234567"})
    birthDate: date = Field(json_schema_extra={"example": "1998-05-15"})

class UpdateCustomerRequest(BaseModel):
    externalId: int = Field(json_schema_extra={"example": 4213})
    fullname: str = Field()
    phone: str = Field(pattern=r"^\+998\d{9}$", json_schema_extra={"example": "+998901234567"})
    birthDate: date = Field(json_schema_extra={"example": "1998-05-15"})

# Product

class CheckProductStockRequest(BaseModel):
    externalIds: List[int] = Field(min_length=1)

# Order

class OrderLineRequest(BaseModel):
    productExternalId: int = Field(json_schema_extra={"example": 8241})
    qty: float = Field(gt=0, json_schema_extra={"example": 2})
    unitPrice: Decimal = Field(ge=0, json_schema_extra={"example": 45000})
    discount: Decimal = Field(default=0, ge=0, json_schema_extra={"example": 5})

class CreateOrderRequest(BaseModel):
    webOrderId: str = Field(json_schema_extra={"example": "WEB-20260804-00001"})
    orderNumber: str = Field(json_schema_extra={"example": "ORD-10001"})
    customerExternalId: int = Field(json_schema_extra={"example": 4213})
    lines: List[OrderLineRequest]
    cashbackUsed: Decimal = Field(default=0, ge=0, json_schema_extra={"example": 3000})
    deliveryAddress: str = Field(json_schema_extra={"example": "Toshkent"})
    deliveryMethod: str = Field(json_schema_extra={"example": "courier"})
    deliveryFee: Decimal = Field( default=0, ge=0, json_schema_extra={"example": 15000})
    paymentMethod: str = Field(json_schema_extra={"example": "payme"})
    paymentStatus: str = Field(json_schema_extra={"example": "paid"})
    paymentTxnId: str | None = Field( default=None, json_schema_extra={"example": "TXN-987654321"})
    createdAt: datetime = Field(json_schema_extra={"example": "2026-08-04T10:15:00"})