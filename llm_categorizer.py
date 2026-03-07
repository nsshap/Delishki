"""Module for categorizing recommendations using LLM."""
import json
from openai import OpenAI
from config import OPENAI_API_KEY, CATEGORIES


class LLMCategorizer:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.categories = CATEGORIES

    def identify_show_category(self, text: str) -> str | None:
        """Detect if user is asking to show a category. Returns category name or None."""
        categories_str = "\n".join([f"- {cat}" for cat in self.categories])
        prompt = f"""Пользователь написал: "{text}"

Он просит ПОКАЗАТЬ список какой-то категории? Если да — верни название категории. Если нет — верни null.

Категории и их алиасы:
- GroceryList: список продуктов, продукты, что купить домой, список покупок, еда
- Movies: фильмы, сериалы, что посмотреть, кино
- Books: книги, что почитать, литература
- PersonalTodoList: мои задачи, мои дела, мой список дел, личные дела
- FamilyTodoList: дела с Сашей, семейные дела, наши дела, совместные дела, список дел семьи, дела семьи, что с Сашей
- ShoppingClothes: одежда, что купить из одежды, гардероб
- ShoppingHome: для дома, товары для дома, что купить домой из вещей
- TravelIdeas: путешествия, куда поехать, идеи для поездок
- LeisureIdeas: досуг, что поделать, мероприятия, куда сходить
- WorkReading: рабочее, статьи для работы, профессиональное
- Courses: курсы, обучение, что поучить
- GiftIdeas: идеи подарков, подарки, что подарить, список подарков, подарки для

Важно: запрос должен быть именно на ПОКАЗ/ПРОСМОТР списка (покажи, что у меня есть, список, открой, посмотреть).
Если это просто фраза без просьбы показать — верни null.

Примеры:
- "покажи дела с Сашей" → "FamilyTodoList"
- "наши дела с Сашей" → "FamilyTodoList"
- "покажи семейные дела" → "FamilyTodoList"
- "покажи список продуктов" → "GroceryList"
- "покажи фильмы" → "Movies"
- "что почитать" → "Books"
- "мои задачи" → "PersonalTodoList"
- "покажи одежду" → "ShoppingClothes"
- "добавь дела с Сашей: погулять" → null (это не показ, а добавление)
- "привет как дела" → null

Верни JSON: {{"category": "название категории или null"}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            result = json.loads(response.choices[0].message.content)
            category = result.get("category")
            if category and category != "null" and category in self.categories:
                return category
            return None
        except Exception as e:
            print(f"Error identifying show category: {e}")
            return None

    def identify_bulk_add(self, text: str, context_category: str = None) -> dict | None:
        """Detect if user wants to add multiple items to a list. Returns {category, items} or None."""
        context_hint = f"Последний показанный список: {context_category}." if context_category else ""
        prompt = f"""Пользователь написал: "{text}"
{context_hint}

Он хочет добавить один или несколько пунктов в список? Списки это: GroceryList, PersonalTodoList, FamilyTodoList, GiftIdeas.

Категории и их алиасы:
- GroceryList: список продуктов, продукты, покупки — еда, напитки, бытовая химия
- PersonalTodoList: мои дела, мои задачи, личные дела
- FamilyTodoList: дела с Сашей, семейные дела, наши дела
- GiftIdeas: идеи подарков, подарки, что подарить, список подарков

Если это запрос на добавление — верни JSON:
{{"category": "название категории", "items": ["пункт1", "пункт2"]}}

Если это НЕ запрос на добавление в список — верни {{"category": null, "items": []}}

Примеры:
- "добавь картошку, молоко и хлеб" → {{"category": "GroceryList", "items": ["картошка", "молоко", "хлеб"]}}
- "добавь в список продуктов: фейри, губка, яйца" → {{"category": "GroceryList", "items": ["фейри", "губка", "яйца"]}}
- "добавь в мои дела: записаться к врачу, оплатить счёт" → {{"category": "PersonalTodoList", "items": ["записаться к врачу", "оплатить счёт"]}}
- "картошка, молоко, хлеб" (если context_category=GroceryList) → {{"category": "GroceryList", "items": ["картошка", "молоко", "хлеб"]}}
- "посмотреть фильм про любовь" → {{"category": null, "items": []}}
- "удали картошку" → {{"category": null, "items": []}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            result = json.loads(response.choices[0].message.content)
            if not result.get("category") or not result.get("items"):
                return None
            return result
        except Exception as e:
            print(f"Error identifying bulk add: {e}")
            return None

    def identify_delete_request(self, text: str) -> dict | None:
        """Detect if user wants to delete items. Returns {action, category, items} or None."""
        prompt = f"""Пользователь написал: "{text}"

Он хочет удалить что-то из списка?

Возможные действия:
- "delete_items" — удалить конкретные пункты по названию
- "delete_by_position" — удалить пункты по номеру (первый, второй, 1, 2, ...)
- "clear_list" — очистить весь список

Категории (если не указана явно — верни null, используем контекст):
- GroceryList: список продуктов, продукты, покупки, список покупок
- PersonalTodoList: мои дела, мои задачи, личные дела
- FamilyTodoList: дела с Сашей, семейные дела, наши дела
- GiftIdeas: идеи подарков, подарки, что подарить

Верни JSON:
{{
  "action": "delete_items" | "delete_by_position" | "clear_list" | null,
  "category": "название категории или null",
  "items": ["название1", "название2"],
  "positions": [1, 2, 4]
}}

Примеры:
- "удали картошку из списка продуктов" → {{"action": "delete_items", "category": "GroceryList", "items": ["картошка"], "positions": []}}
- "я уже купила фейри и молоко" → {{"action": "delete_items", "category": "GroceryList", "items": ["фейри", "молоко"], "positions": []}}
- "удали первый пункт" → {{"action": "delete_by_position", "category": null, "items": [], "positions": [1]}}
- "удали первый, второй и четвёртый" → {{"action": "delete_by_position", "category": null, "items": [], "positions": [1, 2, 4]}}
- "удали 1, 3, 5" → {{"action": "delete_by_position", "category": null, "items": [], "positions": [1, 3, 5]}}
- "удали из этого списка картошку" → {{"action": "delete_items", "category": null, "items": ["картошка"], "positions": []}}
- "очисти весь список продуктов" → {{"action": "clear_list", "category": "GroceryList", "items": [], "positions": []}}
- "очисти этот список" → {{"action": "clear_list", "category": null, "items": [], "positions": []}}
- "добавь картошку" → {{"action": null, "category": null, "items": [], "positions": []}}
- "покажи фильмы" → {{"action": null, "category": null, "items": [], "positions": []}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            result = json.loads(response.choices[0].message.content)
            if result.get("action") is None:
                return None
            return result
        except Exception as e:
            print(f"Error identifying delete request: {e}")
            return None

    def match_items_to_delete(self, requested: list, actual: list) -> list:
        """Match requested item names against actual titles in DB. Returns list of IDs."""
        if not requested or not actual:
            return []
        actual_str = "\n".join([f'- id={item["id"]}: "{item["title"]}"' for item in actual])
        requested_str = ", ".join([f'"{r}"' for r in requested])
        prompt = f"""Пользователь хочет удалить: {requested_str}

Вот что есть в базе:
{actual_str}

Найди совпадения (нечёткий поиск: падежи, опечатки, частичное совпадение).
Верни JSON: {{"ids": ["id1", "id2"]}} — только те id, которые совпадают с запросом.
Если ничего не совпадает — верни {{"ids": []}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("ids", [])
        except Exception as e:
            print(f"Error matching items: {e}")
            return []

    def categorize_multiple(self, text: str, urls: list = None, content_type: str = "text") -> dict:
        """Detect and categorize one or more recommendations from a single message.

        Returns:
            {
                "needs_clarification": bool,
                "question": str | None,
                "items": list[dict]  # each has category/title/description/url/tags/confidence
            }
        """
        if not text or not text.strip():
            return {"needs_clarification": False, "question": None, "items": []}

        categories_str = "\n".join([f"- {cat}" for cat in self.categories])
        urls_str = f"\nСсылки в сообщении: {', '.join(urls)}" if urls else ""

        prompt = f"""Проанализируй сообщение пользователя. Он хочет сохранить одну или несколько рекомендаций.

Сообщение: "{text}"{urls_str}

ПРАВИЛА определения количества записей:
1. Явное перечисление нескольких объектов → отдельная запись для каждого:
   "книги: Атомные привычки, Антихрупкость" → 2 записи Books
   "книга X и фильм Y" → 2 записи в разных категориях
   "посмотри https://A.com и прочитай https://B.com" → 2 записи
2. Один объект → одна запись:
   "фильм Дюна — крутая фантастика" → 1 запись Movies
   "https://somelink.com" → 1 запись
3. Если НЕЯСНО сколько записей создавать (не путать с неясной категорией!) — задай вопрос:
   "книги по продуктивности" — непонятно: это одна книга с таким названием, или нужно несколько?
   Задавай вопрос ТОЛЬКО в редких случаях реальной неоднозначности.

Доступные категории:
{categories_str}

Правила категоризации:
- Books: книги, аудиокниги, литература
- Movies: фильмы, сериалы, YouTube, подкасты, что посмотреть
- ShoppingClothes: одежда, обувь, аксессуары, гардероб
- WorkReading: статьи про продакт-менеджмент, IT, профессиональные блоги, материалы для работы
- LeisureIdeas: театры, концерты, выставки, мероприятия, куда сходить
- TravelIdeas: места для путешествий, отели, маршруты, рестораны в других городах
- ShoppingHome: товары для дома, мебель, декор, бытовая техника
- PersonalTodoList: личные задачи, "надо сделать", "не забыть"
- FamilyTodoList: задачи с упоминанием Саши или семьи
- Courses: онлайн-курсы, мастер-классы, образование
- GroceryList: список продуктов, еда, напитки, бытовая химия
- GiftIdeas: идеи подарков, что подарить, подарки для конкретного человека или повода
- Other: всё остальное
- Для ссылок: youtube.com → Movies, amazon.com → Shopping*, booking.com → TravelIdeas

Верни JSON:
{{
  "needs_clarification": false,
  "question": null,
  "items": [
    {{
      "category": "категория из списка",
      "title": "краткое название (до 100 символов)",
      "description": "описание (до 500 символов)",
      "url": "ссылка или пустая строка",
      "tags": ["тег1", "тег2"],
      "confidence": 0.9
    }}
  ]
}}

Или если нужно уточнение:
{{
  "needs_clarification": true,
  "question": "Конкретный вопрос пользователю о количестве записей",
  "items": []
}}"""

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

            if result.get("needs_clarification"):
                return {"needs_clarification": True, "question": result.get("question"), "items": []}

            validated = []
            for item in result.get("items", []):
                if item.get("category") not in self.categories:
                    item["category"] = "Other"
                item.setdefault("tags", [])
                item.setdefault("confidence", 0.7)
                item.setdefault("url", "")
                item.setdefault("description", "")
                if item.get("category") == "Other":
                    print(f"[OTHER LOG] title={item.get('title')!r} | text={text[:200]!r}")
                validated.append(item)

            return {"needs_clarification": False, "question": None, "items": validated}

        except Exception as e:
            print(f"Error in categorize_multiple: {e}")
            return {"needs_clarification": False, "question": None, "items": []}

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
- "GroceryList" - список продуктов, еда и напитки для покупки домой, "купить домой", перечисление продуктов (овощи, фрукты, молочное, мясо, бытовая химия типа фейри/средство для мытья посуды, хлеб и т.д.)
- "GiftIdeas" - идеи подарков, что подарить конкретному человеку или на конкретный повод (день рождения, праздник), список пожеланий к подарку
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

