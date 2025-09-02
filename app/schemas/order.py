from typing import List, Optional

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    product_id: str
    qty: int = Field(ge=1)


class CustomerIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None


class OrderCreate(BaseModel):
    customer: CustomerIn
    items: List[OrderItemIn]
    comment: Optional[str] = None
    shipping_cents: int = 0
    currency: str = "EUR"


class OrderItemOut(BaseModel):
    id: int
    product_id: str
    qty: int
    item_name: str
    item_price_cents: int

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: str
    status: str
    currency: str
    customer_name: str
    customer_email: Optional[str]
    customer_phone: Optional[str]
    shipping_address: Optional[str]
    shipping_city: Optional[str]
    shipping_postal_code: Optional[str]
    subtotal_cents: int
    shipping_cents: int
    total_cents: int
    comment: Optional[str]
    items: List[OrderItemOut]

    class Config:
        from_attributes = True
