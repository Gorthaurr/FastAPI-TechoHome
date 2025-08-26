from typing import Optional, List
from pydantic import BaseModel


class ImageOut(BaseModel):
    id: int
    path: str
    sort_order: int
    is_primary: bool
    url: Optional[str] = None

    class Config:
        from_attributes = True


class AttributeOut(BaseModel):
    id: int
    key: str
    value: Optional[str]

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: str
    category_id: int
    name: str
    product_url: Optional[str]
    price_raw: Optional[str]
    price_cents: Optional[int]
    description: Optional[str]
    images: Optional[List[ImageOut]] = None
    attributes: Optional[List[AttributeOut]] = None

    class Config:
        from_attributes = True