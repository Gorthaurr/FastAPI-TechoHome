# 🚀 FastAPI Backend - Полная документация API

## 📋 Общая информация

**Base URL:** `http://localhost:8000`  
**API Version:** `v1`  
**Full API URL:** `http://localhost:8000/api/v1`

## 🔧 Запуск Backend

```bash
# Запуск всей системы (Docker + FastAPI)
python scripts/system_launcher.py

# Или через Docker Compose
cd scripts
docker-compose up -d
```

## 📊 Структура данных

### 🏷️ Product (Продукт)
```typescript
interface Product {
  id: string;                    // Уникальный ID продукта (строка)
  category_id: number;           // ID категории
  name: string;                  // Название продукта
  description: string;           // Описание
  price_raw: string;             // Цена в строковом формате (например: "181 272 ₽")
  price_cents: number;           // Цена в копейках (18127200)

  images?: ProductImage[];       // Массив изображений (опционально)
  attributes?: ProductAttribute[]; // Массив атрибутов (опционально)
}
```

### 🖼️ ProductImage (Изображение продукта)
```typescript
interface ProductImage {
  id: number;                    // ID изображения
  product_id: string;            // ID продукта
  path: string;                  // Путь к файлу в MinIO
  filename: string;              // Имя файла
  sort_order: number;            // Порядок сортировки
  is_primary: boolean;           // Главное изображение
  status: string;                // Статус (ready, processing, error)
  url: string;                   // Полный URL для отображения
  urls: {                        // Различные размеры изображений
    original: string;
    thumb: string;
    small: string;
    medium: string;
    large: string;
  };
  file_size?: number;            // Размер файла
  mime_type?: string;            // MIME тип
  width?: number;                // Ширина
  height?: number;               // Высота
  alt_text?: string;             // Alt текст
}
```

### 🏷️ ProductAttribute (Атрибут продукта)
```typescript
interface ProductAttribute {
  id: number;                    // ID атрибута
  product_id: string;            // ID продукта
  key: string;                   // Ключ атрибута (например: "Бренд", "Цвет")
  value: string;                 // Значение атрибута
}
```

### 📂 Category (Категория)
```typescript
interface Category {
  id: number;                    // ID категории
  slug: string;                  // Slug категории
}
```

### 📦 Order (Заказ)
```typescript
interface Order {
  id: string;                    // ID заказа (UUID)
  user_id?: string;              // ID пользователя
  status: string;                // Статус заказа
  total_amount_cents: number;    // Общая сумма в копейках
  created_at: string;            // Дата создания
  updated_at: string;            // Дата обновления
  items: OrderItem[];            // Товары в заказе
}
```

### 🛒 OrderItem (Товар в заказе)
```typescript
interface OrderItem {
  id: string;                    // ID товара в заказе
  order_id: string;              // ID заказа
  product_id: string;            // ID продукта
  quantity: number;              // Количество
  price_cents: number;           // Цена в копейках
  product?: Product;             // Данные продукта (опционально)
}
```

## 🌐 API Endpoints

### 📦 Products (Продукты)

#### 1. Получить список продуктов
```http
GET /api/v1/products
```

**Query Parameters:**
- `page` (number, default: 1) - Номер страницы
- `page_size` (number, default: 20) - Размер страницы
- `category_id` (number, optional) - Фильтр по категории
- `include_images` (boolean, default: false) - Включить изображения
- `include_attributes` (boolean, default: false) - Включить атрибуты

**Пример запроса:**
```typescript
const response = await fetch('http://localhost:8000/api/v1/products?page=1&page_size=2&include_images=true&include_attributes=true');
const data = await response.json();
```

**Пример ответа:**
```json
{
  "items": [
    {
      "id": "9c0382830dcc",
      "category_id": 1,
      "name": "",
      "price_raw": "181 272 ₽",
      "price_cents": 18127200,
      "description": "Общие данные:\n\nБренд для овощей\n\nБренд Kuppersberg Цвет черный Тип French Door Тип установки отдельностоящий Количество компрессоров 1 Уровень шума (дБ) 42 Тип управления сенсорное Мощность замораживания (кг/сут) 12 Класс энергопотребления A++ Хладагент R600a Тип компрессора инверторный Марина от детей Да Общий объем 489 Общий объем холодильной камеры 327 Общий объем морозильной камеры 162 Размораживание холодильной камеры No Frost Размораживание морозильной камеры No Frost Дисплей да Зона свежести Есть Высота (см) 182 Глубина (см) 70.3 Ширина (см) 83.5 Страна производства Китай Гарантия 2 года\n\nчерный",
      "images": [
        {
          "id": 219,
          "path": "products/9c0382830dcc/img_001.png",
          "filename": "img_001.png",
          "sort_order": 0,
          "is_primary": true,
          "status": "ready",
          "url": "https://cdn.yourdomain.com/products/9c0382830dcc/img_001.png",
          "urls": {
            "original": "https://cdn.yourdomain.com/products/9c0382830dcc/img_001.png",
            "thumb": "https://cdn.yourdomain.com/products\\9c0382830dcc\\img_001_thumb.png",
            "small": "https://cdn.yourdomain.com/products\\9c0382830dcc\\img_001_small.png",
            "medium": "https://cdn.yourdomain.com/products\\9c0382830dcc\\img_001_medium.png",
            "large": "https://cdn.yourdomain.com/products\\9c0382830dcc\\img_001_large.png"
          },
          "file_size": null,
          "mime_type": null,
          "width": null,
          "height": null,
          "alt_text": null
        }
      ],
      "attributes": [
        {
          "id": 5318,
          "key": "Бренд",
          "value": "Kuppersberg"
        },
        {
          "id": 5319,
          "key": "Цвет",
          "value": "черный"
        },
        {
          "id": 5320,
          "key": "Тип",
          "value": "French Door"
        },
        {
          "id": 5321,
          "key": "Тип установки",
          "value": "отдельностоящий"
        },
        {
          "id": 5322,
          "key": "Количество компрессоров",
          "value": "1"
        },
        {
          "id": 5323,
          "key": "Уровень шума (дБ)",
          "value": "42"
        },
        {
          "id": 5324,
          "key": "Тип управления",
          "value": "сенсорное"
        },
        {
          "id": 5325,
          "key": "Мощность замораживания (кг/сут)",
          "value": "12"
        },
        {
          "id": 5326,
          "key": "Класс энергопотребления",
          "value": "A++"
        },
        {
          "id": 5327,
          "key": "Хладагент",
          "value": "R600a"
        },
        {
          "id": 5328,
          "key": "Тип компрессора",
          "value": "инверторный"
        },
        {
          "id": 5329,
          "key": "Марина от детей",
          "value": "Да"
        },
        {
          "id": 5330,
          "key": "Общий объем",
          "value": "489"
        },
        {
          "id": 5331,
          "key": "Общий объем холодильной камеры",
          "value": "327"
        },
        {
          "id": 5332,
          "key": "Общий объем морозильной камеры",
          "value": "162"
        },
        {
          "id": 5333,
          "key": "Размораживание холодильной камеры",
          "value": "No Frost"
        },
        {
          "id": 5334,
          "key": "Размораживание морозильной камеры",
          "value": "No Frost"
        },
        {
          "id": 5335,
          "key": "Дисплей",
          "value": "да"
        },
        {
          "id": 5336,
          "key": "Зона свежести",
          "value": "Есть"
        },
        {
          "id": 5337,
          "key": "Высота (см)",
          "value": "182"
        },
        {
          "id": 5338,
          "key": "Глубина (см)",
          "value": "70.3"
        },
        {
          "id": 5339,
          "key": "Ширина (см)",
          "value": "83.5"
        },
        {
          "id": 5340,
          "key": "Страна производства",
          "value": "Китай"
        },
        {
          "id": 5341,
          "key": "Гарантия",
          "value": "2 года"
        }
      ]
    },
    {
      "id": "e220777f7508",
      "category_id": 1,
      "name": "HIBERG RFC-400DX NFGY inverter",
      "price_raw": "109 900 ₽",
      "price_cents": 10990000,
      "description": "Верхнеморозильный отдельностоящий холодильник HIBERG RFC-400DX NFGY inverter оснащен богатым набором функций и стильным дизайном со стеклянным фасадом.\n\nОбщий объем 380 литров достаточно для хранения практически недельного запаса продуктов для большой семьи. Морозильник с полезным объемом 94 л расположен в нижней части холодильника.\n\nУстройство оснащено системой охлаждения Total No Frost, с которой вам не придется больше размораживать холодильник, достаточно обычного ухода раз в 6 месяцев. Полки модели выполнены из закаленного стекла, вместительные выдвижные ящики для овощей и фруктов имеют влажную зону свежести.\n\nХолодильник HIBERG RFC-400DX NFGY оснащен LED-освещением и сенсорным дисплеем с центральным управлением, на котором можно точно контролировать температуру и выбирать нужный режим.\n\nДанная модель имеет такие функции, как «быстрое охлаждение» до +2°С и «быстрая заморозка» с температурой до -32°С. Режим быстрой заморозки автоматически отключается через 26 часов или при активации функции «Smart ECO». Режим «Smart ECO» рекомендуется к использованию, как самый оптимальный и энергоэффективный, чем позволяет обеспечить сохранность продуктов в наилучшем состоянии.\n\nРежим «Отпуск» позволит сэкономить электроэнергию за счет редкого включения компрессора в период долгого отсутствия членов семьи.\n\nПомимо того, в холодильнике предусмотрена функция «Сигнализация открытых дверей», когда зуммер подает звуковой сигнал тревоги, если дверь холодильника остается открытой больше 3 минут.\n\nС функцией «память» холодильник сохранит все настройки в случае отключения питания. Многопоточная система охлаждения создает оптимальную температуру на каждой полке, поэтому продукты дольше остаются свежими.\n\nБезопасный стеклянный фасад холодильника выполнен в цвете «бежевое стекло», а двери модели имеют возможность перенавешивания на другую сторону, что позволит открывать двери в удобном направлении и легко встроить в имеющийся кухонный гарнитур.\n\nОсобенности и преимущества:\n\nинверторный компрессор;\n\nкласс энергоэффективности A++\n\nЭлектронное управление;\n\nрежим «Smart ECO»;\n\nБренд Hiberg Цвет бежевый Тип Верхнеморозильный Тип установки отдельностоящий Количество компрессоров 1 Уровень шума (дБ) 42 Тип управления электронное Мощность замораживания (кг/сут) 4.5 Класс энергопотребления A++ Хладагент R600a Тип компрессора инверторный Общий объем 380 Общий объем холодильной камеры 257 Общий объем морозильной камеры 94 Размораживание холодильной камеры No Frost Размораживание морозильной камеры No Frost Дисплей да Зона свежести Есть Высота (см) 200 Глубина (см) 65.5 Ширина (см) 59.5 Страна производства Китай Гарантия 2 года\n\nбежевый",
      "images": [
        {
          "id": 214,
          "path": "products/e220777f7508/img_001.png",
          "filename": "img_001.png",
          "sort_order": 0,
          "is_primary": true,
          "status": "ready",
          "url": "https://cdn.yourdomain.com/products/e220777f7508/img_001.png",
          "urls": {
            "original": "https://cdn.yourdomain.com/products/e220777f7508/img_001.png",
            "thumb": "https://cdn.yourdomain.com/products\\e220777f7508\\img_001_thumb.png",
            "small": "https://cdn.yourdomain.com/products\\e220777f7508\\img_001_small.png",
            "medium": "https://cdn.yourdomain.com/products\\e220777f7508\\img_001_medium.png",
            "large": "https://cdn.yourdomain.com/products\\e220777f7508\\img_001_large.png"
          },
          "file_size": null,
          "mime_type": null,
          "width": null,
          "height": null,
          "alt_text": null
        }
      ],
      "attributes": [
        {
          "id": 5203,
          "key": "Бренд",
          "value": "Hiberg"
        },
        {
          "id": 5204,
          "key": "Цвет",
          "value": "бежевый"
        },
        {
          "id": 5205,
          "key": "Тип",
          "value": "Верхнеморозильный"
        },
        {
          "id": 5206,
          "key": "Тип установки",
          "value": "отдельностоящий"
        },
        {
          "id": 5207,
          "key": "Количество компрессоров",
          "value": "1"
        },
        {
          "id": 5208,
          "key": "Уровень шума (дБ)",
          "value": "42"
        },
        {
          "id": 5209,
          "key": "Тип управления",
          "value": "электронное"
        },
        {
          "id": 5210,
          "key": "Мощность замораживания (кг/сут)",
          "value": "4.5"
        },
        {
          "id": 5211,
          "key": "Класс энергопотребления",
          "value": "A++"
        },
        {
          "id": 5212,
          "key": "Хладагент",
          "value": "R600a"
        },
        {
          "id": 5213,
          "key": "Тип компрессора",
          "value": "инверторный"
        },
        {
          "id": 5214,
          "key": "Общий объем",
          "value": "380"
        },
        {
          "id": 5215,
          "key": "Общий объем холодильной камеры",
          "value": "257"
        },
        {
          "id": 5216,
          "key": "Общий объем морозильной камеры",
          "value": "94"
        },
        {
          "id": 5217,
          "key": "Размораживание холодильной камеры",
          "value": "No Frost"
        },
        {
          "id": 5218,
          "key": "Размораживание морозильной камеры",
          "value": "No Frost"
        },
        {
          "id": 5219,
          "key": "Дисплей",
          "value": "да"
        },
        {
          "id": 5220,
          "key": "Зона свежести",
          "value": "Есть"
        },
        {
          "id": 5221,
          "key": "Высота (см)",
          "value": "200"
        },
        {
          "id": 5222,
          "key": "Глубина (см)",
          "value": "65.5"
        },
        {
          "id": 5223,
          "key": "Ширина (см)",
          "value": "59.5"
        },
        {
          "id": 5224,
          "key": "Страна производства",
          "value": "Китай"
        },
        {
          "id": 5225,
          "key": "Гарантия",
          "value": "2 года"
        }
      ]
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 5822
  }
}
```

#### 2. Получить продукт по ID
```http
GET /api/v1/products/{product_id}
```

**Path Parameters:**
- `product_id` (string) - ID продукта

**Query Parameters:**
- `include_images` (boolean, default: false) - Включить изображения
- `include_attributes` (boolean, default: false) - Включить атрибуты

**Пример запроса:**
```typescript
const response = await fetch('http://localhost:8000/api/v1/products/9c0382830dcc?include_images=true&include_attributes=true');
const product = await response.json();
```

**Пример ответа:**
```json
{
  "id": "9c0382830dcc",
  "category_id": 1,
  "name": "",
  "price_raw": "181 272 ₽",
  "price_cents": 18127200,
  "description": "Общие данные:\n\nБренд для овощей\n\nБренд Kuppersberg Цвет черный Тип French Door Тип установки отдельностоящий Количество компрессоров 1 Уровень шума (дБ) 42 Тип управления сенсорное Мощность замораживания (кг/сут) 12 Класс энергопотребления A++ Хладагент R600a Тип компрессора инверторный Марина от детей Да Общий объем 489 Общий объем холодильной камеры 327 Общий объем морозильной камеры 162 Размораживание холодильной камеры No Frost Размораживание морозильной камеры No Frost Дисплей да Зона свежести Есть Высота (см) 182 Глубина (см) 70.3 Ширина (см) 83.5 Страна производства Китай Гарантия 2 года\n\nчерный",
  "images": [
    {
      "id": 219,
      "path": "products/9c0382830dcc/img_001.png",
      "filename": "img_001.png",
      "sort_order": 0,
      "is_primary": true,
      "status": "ready",
      "url": "https://cdn.yourdomain.com/products/9c0382830dcc/img_001.png",
      "urls": {
        "original": "https://cdn.yourdomain.com/products/9c0382830dcc/img_001.png",
        "thumb": "https://cdn.yourdomain.com/products\\9c0382830dcc\\img_001_thumb.png",
        "small": "https://cdn.yourdomain.com/products\\9c0382830dcc\\img_001_small.png",
        "medium": "https://cdn.yourdomain.com/products\\9c0382830dcc\\img_001_medium.png",
        "large": "https://cdn.yourdomain.com/products\\9c0382830dcc\\img_001_large.png"
      },
      "file_size": null,
      "mime_type": null,
      "width": null,
      "height": null,
      "alt_text": null
    }
  ],
  "attributes": [
    {
      "id": 5318,
      "key": "Бренд",
      "value": "Kuppersberg"
    },
    {
      "id": 5319,
      "key": "Цвет",
      "value": "черный"
    }
  ]
}
```

### 📂 Categories (Категории)

#### Получить список категорий
```http
GET /api/v1/categories
```

**Пример запроса:**
```typescript
const response = await fetch('http://localhost:8000/api/v1/categories');
const categories = await response.json();
```

**Пример ответа:**
```json
{
  "value": [
    {
      "id": 1,
      "slug": "electronics"
    }
  ],
  "Count": 1
}
```

### 🖼️ Images (Изображения)

#### Получить изображение через CDN
```http
GET /api/v1/cdn/products/{product_id}/{filename}
```

**Path Parameters:**
- `product_id` (string) - ID продукта
- `filename` (string) - Имя файла изображения

**Пример:**
```typescript
// Получить изображение продукта
const imageUrl = `http://localhost:8000/api/v1/cdn/products/9c0382830dcc/img_001.png`;
```

### 📦 Orders (Заказы)

#### Получить список заказов
```http
GET /api/v1/orders
```

**Query Parameters:**
- `page` (number, default: 1) - Номер страницы
- `page_size` (number, default: 20) - Размер страницы
- `user_id` (string, optional) - Фильтр по пользователю

**Пример запроса:**
```typescript
const response = await fetch('http://localhost:8000/api/v1/orders?page=1&page_size=2');
const orders = await response.json();
```

**Пример ответа:**
```json
{
  "items": [],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 0
  }
}
```

#### Получить заказ по ID
```http
GET /api/v1/orders/{order_id}
```

**Path Parameters:**
- `order_id` (string) - ID заказа

**Пример запроса:**
```typescript
const response = await fetch('http://localhost:8000/api/v1/orders/123e4567-e89b-12d3-a456-426614174000');
const order = await response.json();
```

### 🔍 Health Check

#### Проверить статус API
```http
GET /healthz
```

**Пример запроса:**
```typescript
const response = await fetch('http://localhost:8000/healthz');
const health = await response.json();
```

**Пример ответа:**
```json
{
  "status": "ok"
}
```

## 🎯 Redux Store Structure

### 📦 Products Slice
```typescript
interface ProductsState {
  items: Product[];
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
  filters: {
    category_id?: number;
    include_images: boolean;
    include_attributes: boolean;
  };
}

// Actions
const fetchProducts = createAsyncThunk(
  'products/fetchProducts',
  async (params: { page?: number; page_size?: number; category_id?: number }) => {
    const response = await fetch(`/api/v1/products?${new URLSearchParams(params)}`);
    return response.json();
  }
);

const fetchProductById = createAsyncThunk(
  'products/fetchProductById',
  async (productId: string) => {
    const response = await fetch(`/api/v1/products/${productId}?include_images=true&include_attributes=true`);
    return response.json();
  }
);
```

### 🛒 Cart Slice
```typescript
interface CartState {
  items: CartItem[];
  loading: boolean;
  error: string | null;
}

interface CartItem {
  product_id: string;
  quantity: number;
  product?: Product; // Загружается отдельно
}

// Actions
const addToCart = createAction<{ product_id: string; quantity: number }>('cart/addToCart');
const removeFromCart = createAction<string>('cart/removeFromCart');
const updateQuantity = createAction<{ product_id: string; quantity: number }>('cart/updateQuantity');
```

### 📦 Orders Slice
```typescript
interface OrdersState {
  items: Order[];
  currentOrder: Order | null;
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}

// Actions
const fetchOrders = createAsyncThunk(
  'orders/fetchOrders',
  async (params: { page?: number; page_size?: number }) => {
    const response = await fetch(`/api/v1/orders?${new URLSearchParams(params)}`);
    return response.json();
  }
);

const createOrder = createAsyncThunk(
  'orders/createOrder',
  async (orderData: { items: CartItem[]; user_id?: string }) => {
    const response = await fetch('/api/v1/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData)
    });
    return response.json();
  }
);
```

## 🎨 React Components Examples

### 📦 ProductList Component
```typescript
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchProducts } from '../store/productsSlice';

const ProductList: React.FC = () => {
  const dispatch = useDispatch();
  const { items, loading, error, pagination } = useSelector((state: RootState) => state.products);

  useEffect(() => {
    dispatch(fetchProducts({ page: 1, page_size: 20, include_images: true }));
  }, [dispatch]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="products-grid">
      {items.map(product => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
};
```

### 🖼️ ProductCard Component
```typescript
interface ProductCardProps {
  product: Product;
}

const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const primaryImage = product.images?.find(img => img.is_primary);
  
  return (
    <div className="product-card">
      {primaryImage && (
        <img 
          src={primaryImage.url} 
          alt={primaryImage.alt_text || product.name}
          className="product-image"
        />
      )}
      <h3>{product.name}</h3>
      <p className="price">{product.price_raw}</p>
      <button onClick={() => addToCart(product.id)}>
        Add to Cart
      </button>
    </div>
  );
};
```

### 🛒 Cart Component
```typescript
const Cart: React.FC = () => {
  const { items } = useSelector((state: RootState) => state.cart);
  const dispatch = useDispatch();

  const total = items.reduce((sum, item) => {
    const product = item.product;
    return sum + (product ? product.price_cents * item.quantity : 0);
  }, 0);

  return (
    <div className="cart">
      <h2>Shopping Cart</h2>
      {items.map(item => (
        <CartItem key={item.product_id} item={item} />
      ))}
      <div className="cart-total">
        Total: {(total / 100).toFixed(2)} ₽
      </div>
      <button onClick={() => dispatch(createOrder({ items }))}>
        Checkout
      </button>
    </div>
  );
};
```

## 🔧 Environment Variables

Создайте `.env` файл в корне фронтенд проекта:

```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_API_VERSION=v1
REACT_APP_CDN_BASE_URL=http://localhost:8000/api/v1/cdn
```

## 🚀 Quick Start для Frontend

1. **Создайте React проект:**
```bash
npx create-react-app frontend --template typescript
cd frontend
```

2. **Установите зависимости:**
```bash
npm install @reduxjs/toolkit react-redux axios
```

3. **Настройте Redux Store:**
```typescript
// store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import productsReducer from './productsSlice';
import cartReducer from './cartSlice';
import ordersReducer from './ordersSlice';

export const store = configureStore({
  reducer: {
    products: productsReducer,
    cart: cartReducer,
    orders: ordersReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

4. **Запустите Backend:**
```bash
# В папке backend
python scripts/system_launcher.py
```

5. **Запустите Frontend:**
```bash
# В папке frontend
npm start
```

## 📝 Важные замечания

1. **ID продуктов** - это строки, а не числа (например: "9c0382830dcc")
2. **Цены** хранятся в копейках (делите на 100 для отображения)
3. **Изображения** доступны через CDN endpoint
4. **Пагинация** поддерживается для продуктов и заказов
5. **Фильтрация** по категориям доступна для продуктов
6. **Атрибуты продуктов** содержат технические характеристики
7. **Всего продуктов в БД:** 5822

## 🔗 Полезные ссылки

- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Health Check:** http://localhost:8000/healthz
- **MinIO Console:** http://localhost:9001 (для просмотра изображений)
- **pgAdmin:** http://localhost:5050 (для просмотра БД)

---

**Удачи с разработкой фронтенда! 🚀**
