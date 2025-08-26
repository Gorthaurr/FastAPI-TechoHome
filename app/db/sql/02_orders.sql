-- =========================
-- ДОБАВЛЕНИЕ ТАБЛИЦ ЗАКАЗОВ
-- =========================
-- Этот файл добавляет таблицы заказов к существующей схеме каталога
-- Используется, если у вас уже есть таблицы categories/products/product_images/product_attributes

-- Расширение для генерации UUID
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================
-- ТАБЛИЦА ЗАКАЗОВ
-- =========================
CREATE TABLE IF NOT EXISTS public.orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status varchar(32) NOT NULL DEFAULT 'pending',
    currency varchar(3) NOT NULL DEFAULT 'EUR',

    -- Данные клиента
    customer_name text NOT NULL,
    customer_email text,
    customer_phone text,
    shipping_address text,
    shipping_city text,
    shipping_postal_code text,

    -- Финансовые данные
    subtotal_cents integer NOT NULL DEFAULT 0,
    shipping_cents integer NOT NULL DEFAULT 0,
    total_cents integer NOT NULL DEFAULT 0,

    -- Дополнительная информация
    comment text,

    -- Временные метки
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    -- Ограничения
    CONSTRAINT ck_orders_status CHECK (status in ('pending','paid','canceled','shipped','completed'))
);

-- =========================
-- ТАБЛИЦА ПОЗИЦИЙ ЗАКАЗА
-- =========================
CREATE TABLE IF NOT EXISTS public.order_items (
    id bigserial PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    product_id varchar(64) NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,

    -- Данные позиции
    qty integer NOT NULL CHECK (qty > 0),
    item_name text NOT NULL,
    item_price_cents integer NOT NULL CHECK (item_price_cents >= 0)
);

-- =========================
-- ИНДЕКСЫ
-- =========================
CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON public.order_items(order_id);

-- =========================
-- ТРИГГЕР ДЛЯ ОБНОВЛЕНИЯ updated_at
-- =========================
-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автоматического обновления updated_at при изменении записи
DROP TRIGGER IF EXISTS trg_orders_updated_at ON public.orders;
CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON public.orders
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();