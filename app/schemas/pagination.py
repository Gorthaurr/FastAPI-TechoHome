"""
Схемы для пагинации.
"""

from pydantic import BaseModel


class PageMeta(BaseModel):
    """
    Метаданные пагинации.
    
    Attributes:
        page: Номер текущей страницы
        page_size: Размер страницы
        total: Общее количество записей
    """
    
    page: int
    page_size: int
    total: int