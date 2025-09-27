-- Оптимизация производительности запросов товаров
-- Добавляем индексы для часто используемых полей в ORDER BY и WHERE

-- Индекс для сортировки по названию
CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);

-- Индекс для сортировки по цене
CREATE INDEX IF NOT EXISTS idx_products_price_cents ON products (price_cents);

-- Составной индекс для фильтрации по категории и сортировки по цене
CREATE INDEX IF NOT EXISTS idx_products_category_price ON products (category_id, price_cents);

-- Составной индекс для фильтрации по категории и сортировки по названию
CREATE INDEX IF NOT EXISTS idx_products_category_name ON products (category_id, name);

-- GIN индекс для поиска по названию (ILIKE) - если используется часто
-- CREATE INDEX IF NOT EXISTS idx_products_name_gin ON products USING gin (to_tsvector('russian', name));

-- Индексы для категорий
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories (slug);
