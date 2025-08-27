-- =========================
-- РАСШИРЕНИЕ ТАБЛИЦЫ ИЗОБРАЖЕНИЙ
-- =========================
-- Этот файл добавляет новые поля к таблице product_images для поддержки
-- расширенных метаданных, статусов и обработки изображений

-- Добавление новых полей к таблице product_images
ALTER TABLE public.product_images 
ADD COLUMN IF NOT EXISTS filename varchar(255),
ADD COLUMN IF NOT EXISTS status varchar(32) DEFAULT 'ready',
ADD COLUMN IF NOT EXISTS file_size integer,
ADD COLUMN IF NOT EXISTS mime_type varchar(100),
ADD COLUMN IF NOT EXISTS width integer,
ADD COLUMN IF NOT EXISTS height integer,
ADD COLUMN IF NOT EXISTS alt_text text,
ADD COLUMN IF NOT EXISTS image_metadata jsonb,
ADD COLUMN IF NOT EXISTS uploaded_at timestamptz DEFAULT now(),
ADD COLUMN IF NOT EXISTS processed_at timestamptz,
ADD COLUMN IF NOT EXISTS error_message text;

-- Обновление значений по умолчанию для существующих записей
UPDATE public.product_images 
SET 
    status = 'ready',
    uploaded_at = now()
WHERE status IS NULL;

-- Добавление индексов для новых полей
CREATE INDEX IF NOT EXISTS ix_product_images_status ON public.product_images(status);
CREATE INDEX IF NOT EXISTS ix_product_images_uploaded_at ON public.product_images(uploaded_at);
CREATE INDEX IF NOT EXISTS ix_product_images_filename ON public.product_images(filename);

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

-- Добавление комментариев к полям
COMMENT ON COLUMN public.product_images.filename IS 'Оригинальное имя загруженного файла';
COMMENT ON COLUMN public.product_images.status IS 'Статус обработки изображения: uploading/processing/ready/error';
COMMENT ON COLUMN public.product_images.file_size IS 'Размер файла в байтах';
COMMENT ON COLUMN public.product_images.mime_type IS 'MIME тип файла';
COMMENT ON COLUMN public.product_images.width IS 'Ширина изображения в пикселях';
COMMENT ON COLUMN public.product_images.height IS 'Высота изображения в пикселях';
COMMENT ON COLUMN public.product_images.alt_text IS 'Альтернативный текст для SEO и доступности';
COMMENT ON COLUMN public.product_images.image_metadata IS 'Дополнительные метаданные в формате JSON';
COMMENT ON COLUMN public.product_images.uploaded_at IS 'Дата и время загрузки файла';
COMMENT ON COLUMN public.product_images.processed_at IS 'Дата и время завершения обработки';
COMMENT ON COLUMN public.product_images.error_message IS 'Сообщение об ошибке при обработке';

-- Создание функции для автоматического обновления processed_at
CREATE OR REPLACE FUNCTION public.set_image_processed_at() RETURNS trigger AS $$
BEGIN
    IF NEW.status = 'ready' AND OLD.status != 'ready' THEN
        NEW.processed_at = now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Создание триггера для автоматического обновления processed_at
DROP TRIGGER IF EXISTS trg_product_images_processed_at ON public.product_images;
CREATE TRIGGER trg_product_images_processed_at
    BEFORE UPDATE ON public.product_images
    FOR EACH ROW EXECUTE FUNCTION public.set_image_processed_at();

-- Создание представления для удобного просмотра изображений
CREATE OR REPLACE VIEW public.product_images_view AS
SELECT 
    pi.id,
    pi.product_id,
    pi.path,
    pi.filename,
    pi.sort_order,
    pi.is_primary,
    pi.status,
    pi.file_size,
    pi.mime_type,
    pi.width,
    pi.height,
    pi.alt_text,
    pi.uploaded_at,
    pi.processed_at,
    pi.error_message,
    p.name as product_name,
    CASE 
        WHEN pi.status = 'ready' THEN true 
        ELSE false 
    END as is_available
FROM public.product_images pi
JOIN public.products p ON pi.product_id = p.id
ORDER BY pi.product_id, pi.sort_order, pi.id;

-- Добавление комментария к представлению
COMMENT ON VIEW public.product_images_view IS 'Представление для удобного просмотра изображений товаров с информацией о товаре';
