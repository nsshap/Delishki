"""Module for categorizing recommendations using LLM."""
import json
from openai import OpenAI
from config import OPENAI_API_KEY, CATEGORIES


class LLMCategorizer:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.categories = CATEGORIES

    def categorize(self, text: str, url: str = None, content_type: str = "text") -> dict:
        """Categorize recommendation using LLM.
        
        Args:
            text: Text content to categorize
            url: Optional URL if present
            content_type: Type of content - "text", "link", "image", or "image_with_text"
        """
        if not text or not text.strip():
            return {
                "category": "Other",
                "title": "Без названия",
                "description": "",
                "url": url or "",
                "tags": [],
                "confidence": 0.5
            }

        # Prepare content type context
        content_type_context = {
            "text": "Это текстовое сообщение. Проанализируй содержимое сообщения для определения категории.",
            "link": "Это ссылка. Проанализируй домен, путь URL и контекст ссылки для определения категории.",
            "image": "Это изображение. Текст уже извлечен из изображения - используй его для категоризации.",
            "image_with_text": "Это изображение с подписью. Учти и текст из изображения, и подпись для категоризации."
        }
        type_instruction = content_type_context.get(content_type, content_type_context["text"])

        # Prepare prompt
        categories_str = "\n".join([f"- {cat}" for cat in self.categories])
        prompt = f"""Проанализируй следующую рекомендацию и определи её категорию, название, описание, теги и уверенность.

Тип контента: {content_type}
{type_instruction}

Рекомендация:
{text}
{f'Ссылка: {url}' if url else ''}

Доступные категории:
{categories_str}

Верни ответ в формате JSON:
{{
    "category": "название категории из списка",
    "title": "краткое название рекомендации",
    "description": "краткое описание или заметка",
    "tags": ["тег1", "тег2"],
    "confidence": 0.85
}}

Правила категоризации:
- "Books" - книги, аудиокниги, литература, художественная и нехудожественная проза, что почитать для удовольствия
- "Movies" - фильмы, сериалы, YouTube видео, документалки, подкасты для прослушивания, что посмотреть
- "ShoppingClothes" - одежда, обувь, аксессуары, модные бренды, магазины одежды, вещи для гардероба
- "WorkReading" - статьи про продакт менеджмент, IT, продакт маркетинг, профессиональные блоги, техническая документация, материалы для работы и профессионального развития
- "LeisureIdeas" - театры, спектакли, зоопарки, парки, концерты, выставки, музеи, развлечения, мероприятия в городе
- "TravelIdeas" - места для путешествий, города, страны, отели, маршруты, достопримечательности, рестораны в других городах/странах, идеи для поездок
- "ShoppingHome" - товары для дома, мебель, декор, бытовая техника, посуда, текстиль, предметы интерьера
- "PersonalTodoList" - мои личные задачи, напоминания, "надо сделать", "не забыть", планы — без упоминания семьи или конкретных имён (Саша и др.)
- "FamilyTodoList" - задачи для семьи, список дел семьи, дела с упоминанием Саши или других членов семьи, совместные планы
- "Courses" - онлайн-курсы, офлайн-курсы, мастер-классы, обучение, образовательные программы, дипломы, практики и методики саморазвития
- "Other" - все остальное, что не подходит под другие категории, или если не уверен

Дополнительные правила:
- title: краткое название (до 100 символов), извлеки основное название из текста/ссылки/изображения
- description: описание или контекст (до 500 символов), что это и почему интересно
- tags: массив из 1-5 релевантных тегов (например: ["фильм", "комедия"], ["книга", "фантастика"], ["ресторан", "москва"], ["концерт", "рок"], ["одежда", "зима"])
- confidence: число от 0 до 1, показывающее уверенность в категоризации (0.9 = очень уверен, 0.5 = не уверен)
- Для ссылок: анализируй домен (например, youtube.com → Movies, amazon.com → ShoppingClothes/ShoppingHome, booking.com → TravelIdeas)
- Для изображений: используй извлеченный текст и визуальный контекст для определения категории"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты помощник для категоризации рекомендаций. Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            result["url"] = url or ""
            if result.get("category") == "Other":
                print(f"[OTHER LOG] content_type={content_type} | text={text[:200]!r} | url={url!r}")
            # Ensure tags and confidence are present
            if "tags" not in result:
                result["tags"] = []
            if "confidence" not in result:
                result["confidence"] = 0.7
            return result

        except Exception as e:
            print(f"Error categorizing with LLM: {e}")
            return {
                "category": "Other",
                "title": text[:50] if text else "Без названия",
                "description": text[:200] if text else "",
                "url": url or "",
                "tags": [],
                "confidence": 0.5
            }

