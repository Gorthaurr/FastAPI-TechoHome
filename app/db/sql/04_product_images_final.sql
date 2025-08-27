-- Миграция 04: Финальные улучшения для таблицы product_images
-- Добавляет недостающие поля, индексы и оптимизации

-- Добавление недостающих полей
ALTER TABLE public.product_images 
ADD COLUMN IF NOT EXISTS file_size integer,
ADD COLUMN IF NOT EXISTS mime_type varchar(100),
ADD COLUMN IF NOT EXISTS width integer,
ADD COLUMN IF NOT EXISTS height integer,
ADD COLUMN IF NOT EXISTS alt_text text,
ADD COLUMN IF NOT EXISTS image_metadata jsonb,
ADD COLUMN IF NOT EXISTS uploaded_at timestamptz DEFAULT now(),
ADD COLUMN IF NOT EXISTS processed_at timestamptz,
ADD COLUMN IF NOT EXISTS error_message text;

-- Добавление комментариев к полям
COMMENT ON COLUMN public.product_images.file_size IS 'Размер файла в байтах';
COMMENT ON COLUMN public.product_images.mime_type IS 'MIME тип файла';
COMMENT ON COLUMN public.product_images.width IS 'Ширина изображения в пикселях';
COMMENT ON COLUMN public.product_images.height IS 'Высота изображения в пикселях';
COMMENT ON COLUMN public.product_images.alt_text IS 'Альтернативный текст для SEO и доступности';
COMMENT ON COLUMN public.product_images.image_metadata IS 'Дополнительные метаданные в формате JSON';
COMMENT ON COLUMN public.product_images.uploaded_at IS 'Дата и время загрузки файла';
COMMENT ON COLUMN public.product_images.processed_at IS 'Дата и время завершения обработки';
COMMENT ON COLUMN public.product_images.error_message IS 'Сообщение об ошибке при обработке';

-- Добавление ограничений
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints 
        WHERE constraint_name = 'ck_product_images_status'
    ) THEN
        ALTER TABLE public.product_images 
        ADD CONSTRAINT ck_product_images_status 
        CHECK (status in ('uploading','processing','ready','error'));
    END IF;
END $$;

-- Добавление индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS ix_product_images_product_id ON public.product_images(product_id);
CREATE INDEX IF NOT EXISTS ix_product_images_status ON public.product_images(status);
CREATE INDEX IF NOT EXISTS ix_product_images_uploaded_at ON public.product_images(uploaded_at);
CREATE INDEX IF NOT EXISTS ix_product_images_processed_at ON public.product_images(processed_at);
CREATE INDEX IF NOT EXISTS ix_product_images_sort_order ON public.product_images(sort_order);
CREATE INDEX IF NOT EXISTS ix_product_images_is_primary ON public.product_images(is_primary);

-- Составной индекс для быстрого поиска изображений товара по статусу и порядку
CREATE INDEX IF NOT EXISTS ix_product_images_product_status_sort 
ON public.product_images(product_id, status, sort_order);

-- Индекс для поиска по метаданным (GIN для JSONB)
CREATE INDEX IF NOT EXISTS ix_product_images_metadata_gin 
ON public.product_images USING GIN (image_metadata);

-- Триггер для автоматического обновления processed_at
CREATE OR REPLACE FUNCTION update_processed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'ready' AND OLD.status != 'ready' THEN
        NEW.processed_at = now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_processed_at ON public.product_images;
CREATE TRIGGER trigger_update_processed_at
    BEFORE UPDATE ON public.product_images
    FOR EACH ROW
    EXECUTE FUNCTION update_processed_at();

-- Представление для удобного получения статистики изображений
CREATE OR REPLACE VIEW v_product_images_stats AS
SELECT 
    product_id,
    COUNT(*) as total_images,
    COUNT(*) FILTER (WHERE status = 'ready') as ready_images,
    COUNT(*) FILTER (WHERE status = 'processing') as processing_images,
    COUNT(*) FILTER (WHERE status = 'uploading') as uploading_images,
    COUNT(*) FILTER (WHERE status = 'error') as error_images,
    COUNT(*) FILTER (WHERE is_primary = true) as primary_images,
    SUM(file_size) as total_size,
    AVG(file_size) as avg_size,
    MIN(uploaded_at) as first_upload,
    MAX(uploaded_at) as last_upload
FROM public.product_images
GROUP BY product_id;

-- Представление для получения готовых изображений с URL
CREATE OR REPLACE VIEW v_ready_product_images AS
SELECT 
    pi.id,
    pi.product_id,
    pi.path,
    pi.filename,
    pi.sort_order,
    pi.is_primary,
    pi.file_size,
    pi.mime_type,
    pi.width,
    pi.height,
    pi.alt_text,
    pi.uploaded_at,
    pi.processed_at,
    -- Формируем URL для разных размеров
    CASE 
        WHEN pi.path LIKE '/static/%' THEN pi.path
        ELSE '/static/' || pi.path
    END as original_url,
    CASE 
        WHEN pi.path LIKE '/static/%' THEN pi.path || '_thumb.jpg'
        ELSE '/static/' || pi.path || '_thumb.jpg'
    END as thumb_url,
    CASE 
        WHEN pi.path LIKE '/static/%' THEN pi.path || '_small.jpg'
        ELSE '/static/' || pi.path || '_small.jpg'
    END as small_url,
    CASE 
        WHEN pi.path LIKE '/static/%' THEN pi.path || '_medium.jpg'
        ELSE '/static/' || pi.path || '_medium.jpg'
    END as medium_url,
    CASE 
        WHEN pi.path LIKE '/static/%' THEN pi.path || '_large.jpg'
        ELSE '/static/' || pi.path || '_large.jpg'
    END as large_url
FROM public.product_images pi
WHERE pi.status = 'ready'
ORDER BY pi.product_id, pi.sort_order, pi.id;

-- Функция для очистки старых изображений со статусом 'error'
CREATE OR REPLACE FUNCTION cleanup_failed_images(days_old integer DEFAULT 7)
RETURNS integer AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM public.product_images 
    WHERE status = 'error' 
    AND uploaded_at < now() - interval '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения размера всех изображений товара
CREATE OR REPLACE FUNCTION get_product_images_size(product_id_param varchar(64))
RETURNS bigint AS $$
DECLARE
    total_size bigint;
BEGIN
    SELECT COALESCE(SUM(file_size), 0) INTO total_size
    FROM public.product_images
    WHERE product_id = product_id_param;
    
    RETURN total_size;
END;
$$ LANGUAGE plpgsql;

-- Добавление комментариев к представлениям и функциям
COMMENT ON VIEW v_product_images_stats IS 'Статистика изображений по товарам';
COMMENT ON VIEW v_ready_product_images IS 'Готовые изображения товаров с URL';
COMMENT ON FUNCTION cleanup_failed_images(integer) IS 'Очистка старых изображений со статусом error';
COMMENT ON FUNCTION get_product_images_size(varchar) IS 'Получение общего размера изображений товара';

-- Обновление существующих записей (если есть)
UPDATE public.product_images 
SET 
    status = COALESCE(status, 'ready'),
    uploaded_at = COALESCE(uploaded_at, now()),
    sort_order = COALESCE(sort_order, 0),
    is_primary = COALESCE(is_primary, false)
WHERE status IS NULL 
   OR uploaded_at IS NULL 
   OR sort_order IS NULL 
   OR is_primary IS NULL;

-- Создание уникального индекса для предотвращения дублирования главных изображений
CREATE UNIQUE INDEX IF NOT EXISTS uq_product_primary_image 
ON public.product_images(product_id) 
WHERE is_primary = true;

-- Добавление комментария к таблице
COMMENT ON TABLE public.product_images IS 'Изображения товаров с поддержкой обработки и метаданных';
