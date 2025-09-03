"""
Эндпоинты для автодополнения адресов с использованием DaData API.

Обеспечивает безопасное получение подсказок адресов через бэкенд.
"""

import httpx
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

# Модели данных
class AddressSuggestionData(BaseModel):
    postal_code: Optional[str] = None
    country: str = "Россия"
    region: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    flat: Optional[str] = None

class AddressSuggestion(BaseModel):
    value: str
    unrestricted_value: str
    data: AddressSuggestionData

class AddressSuggestionsResponse(BaseModel):
    suggestions: List[AddressSuggestion]

# Создание роутера
router = APIRouter()

# Конфигурация DaData API
DADATA_API_KEY = "2841e3c39665f20477c905e694b3a30a0d718007"  # Настоящий ключ
DADATA_API_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"

@router.get("/suggestions", response_model=AddressSuggestionsResponse)
async def get_address_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Поисковый запрос адреса"),
    count: int = Query(10, ge=1, le=20, description="Количество результатов")
):
    """
    Получение подсказок адресов с использованием DaData API.

    - **q**: Поисковый запрос (минимум 1 символ)
    - **count**: Количество результатов (1-20)
    """

    try:
        # Используем настоящий DaData API
        if DADATA_API_KEY:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    DADATA_API_URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Token {DADATA_API_KEY}",
                        "Accept": "application/json",
                    },
                    json={
                        "query": q,
                        "count": count,
                        "locations": [{"country": "Россия"}]
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    suggestions = data.get("suggestions", [])
                    return {"suggestions": suggestions}
                else:
                    print(f"DaData API error: {response.status_code}, {response.text}")
                    return {"suggestions": []}

        # Fallback если нет ключа
        print("DaData API key not configured")
        return {"suggestions": []}

    except Exception as e:
        print(f"Address suggestions error: {e}")
        return {"suggestions": []}