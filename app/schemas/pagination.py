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
        total_pages: Общее количество страниц
    """

    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def create(cls, page: int, page_size: int, total: int) -> "PageMeta":
        """
        Создает экземпляр PageMeta с автоматическим расчетом total_pages.

        Args:
            page: Номер текущей страницы
            page_size: Размер страницы
            total: Общее количество записей

        Returns:
            PageMeta: Экземпляр с рассчитанными метаданными
        """
        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1
        return cls(page=page, page_size=page_size, total=total, total_pages=total_pages)
