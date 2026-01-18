"""Module for processing images and extracting text using LLM Vision API."""
import base64
from openai import OpenAI
from telegram import Update
from config import OPENAI_API_KEY


async def download_image(update: Update, context) -> bytes:
    """Download image from Telegram message and return as bytes."""
    photo = update.message.photo[-1]  # Get highest resolution
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()
    return bytes(image_bytes)


def get_image_mime_type(image_bytes: bytes) -> str:
    """Determine image MIME type from bytes."""
    if image_bytes.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    elif image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):
        return 'image/gif'
    elif image_bytes.startswith(b'WEBP', 8):
        return 'image/webp'
    else:
        # Default to JPEG if unknown
        return 'image/jpeg'


def get_file_extension_from_mime_type(mime_type: str) -> str:
    """Get file extension from MIME type."""
    mime_to_ext = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp',
        'image/svg+xml': 'svg',
        'image/tiff': 'tiff',
        'image/heic': 'heic'
    }
    return mime_to_ext.get(mime_type, 'jpg')


def image_to_base64(image_bytes: bytes) -> tuple[str, str]:
    """Convert image bytes to base64 string and return with MIME type."""
    mime_type = get_image_mime_type(image_bytes)
    base64_str = base64.b64encode(image_bytes).decode('utf-8')
    return base64_str, mime_type


async def extract_text_from_image_with_llm(image_bytes: bytes) -> str:
    """Extract text and information from image using OpenAI Vision API."""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Convert image to base64 and get MIME type
        base64_image, mime_type = image_to_base64(image_bytes)
        
        # Use OpenAI Vision API to extract text and understand image content
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Проанализируй это изображение и извлеки всю информацию для категоризации рекомендации.

Внимательно извлеки:
1. Название/заголовок - основное название книги, фильма, товара, места и т.д.
2. Тип контента - определи, что это (книга, фильм, сериал, товар для покупки, место для посещения, статья, концерт и т.д.)
3. Ссылки и URL - все ссылки, которые видны на изображении (полные URL)
4. Описание - краткое описание или контекст того, что изображено
5. Ключевые слова - важные слова, которые помогут определить категорию (жанр, тип товара, локация и т.д.)

Если это скриншот с рекомендацией (книга, фильм, место, товар, статья и т.д.), извлеки:
- Полное название
- Автор/режиссер/бренд (если есть)
- Описание или краткое содержание
- Все ссылки (URL)
- Дополнительную информацию, которая поможет понять категорию

Верни структурированную информацию: сначала название, затем описание, затем ссылки, затем дополнительные детали."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        extracted_text = response.choices[0].message.content
        return extracted_text.strip() if extracted_text else ""
    except Exception as e:
        print(f"Error extracting text from image with LLM: {e}")
        return ""


async def process_image_message(update: Update, context) -> tuple[str, bytes]:
    """Process image message and return extracted text and image bytes using LLM."""
    image_bytes = await download_image(update, context)
    text = await extract_text_from_image_with_llm(image_bytes)
    return text, image_bytes


async def get_image_file_url(update: Update, context) -> str:
    """Get Telegram file URL for the image."""
    if update.message.photo:
        photo = update.message.photo[-1]  # Get highest resolution
        file = await context.bot.get_file(photo.file_id)
        return file.file_path  # This returns the file path on Telegram servers
    return None


