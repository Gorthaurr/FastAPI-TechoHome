# FastAPI/app/schemas/products.py
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    path: str
    sort_order: int
    is_primary: bool
    url: Optional[str] = None


class AttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    value: Optional[str]


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    category_id: int
    name: str
    product_url: Optional[str]
    price_raw: Optional[str]
    price_cents: Optional[int]
    description: Optional[str]
    images: Optional[List[ImageOut]] = None
    attributes: Optional[List[AttributeOut]] = None
