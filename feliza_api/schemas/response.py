from datetime import datetime, date
from typing import Generic, TypeVar
from math import ceil


T = TypeVar("T")

from pydantic import BaseModel

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None

class PageResponse(BaseModel, Generic[T]):
    page: int
    size: int
    totalElements: int = 0
    totalPages: int = 0
    content: list[T] = []

    @classmethod
    def empty(cls, page: int = 1, size: int = 10):
        return cls(
            page=page,
            size=size,
            totalElements=0,
            totalPages=0,
            content=[],
        )

    @classmethod
    def of(cls, content: list[T], page: int, size: int, total_elements: int):
        return cls(
            page=page,
            size=size,
            totalElements=total_elements,
            totalPages=ceil(total_elements / size) if total_elements else 0,
            content=content,
        )

# Customer
class CustomerResponse(BaseModel):
    externalId: int | None = None
    fullname: str | None = None
    phone: str | None = None
    birthDate: date | None = None
    registrationStatus: str | None = None

class OrderProductResponse(BaseModel):
    externalId: int | None = None
    name: str
    quantity: float
    price: float
    discount_percent: float
    discount_amount: float


class OrderRewardResponse(BaseModel):
    type: str
    name: str
    amount: float


class OrderResponse(BaseModel):
    webOrderId: str
    number: str
    status: str
    date: datetime
    amount: float

    tags: list[str]
    orderSource: str

    products: list[OrderProductResponse]

    rewards: list[OrderRewardResponse]

# Cashback
class CashbackResponse(BaseModel):
    date: datetime
    description: str
    earned: float
    used: float

# Product
class ProductResponse(BaseModel):
    externalId: int
    price: float
    name: str
    quantity: float

class BranchStockResponse(BaseModel):
    warehouseId: int
    name: str
    quantity: float

class OnHandProductResponse(BaseModel):
    externalId: int
    onHand: float
    branches: list[BranchStockResponse] = []

# Order
class CreateOrderResponse(BaseModel):
    webOrderId: str
    name: str