"""Main Telegram bot for processing recommendations."""
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, validate_config
from image_processor import process_image_message
from audio_processor import transcribe_audio
from llm_categorizer import LLMCategorizer
from storage_factory import get_storage


class RecommendationBot:
    def __init__(self):
        self.categorizer = LLMCategorizer()
        self.storage = get_storage()

    def extract_url(self, text: str) -> str:
        """Extract first URL from text."""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        match = url_pattern.search(text)
        return match.group(0) if match else ""

    def extract_urls(self, text: str) -> list:
        """Extract all URLs from text."""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return url_pattern.findall(text)

    async def _process_recommendation(
        self, update, context, text: str, urls: list,
        content_type: str, image_file_url: str = None, image_bytes: bytes = None
    ):
        """Categorize and save one or more recommendations. Handles clarification flow."""
        result = self.categorizer.categorize_multiple(text, urls, content_type)

        if result["needs_clarification"]:
            context.user_data["pending_clarification"] = {
                "text": text,
                "urls": urls,
                "content_type": content_type,
                "image_file_url": image_file_url,
                "image_bytes": image_bytes,
            }
            await update.message.reply_text(result["question"])
            return

        items = result["items"]
        if not items:
            await update.message.reply_text("❌ Не удалось определить рекомендацию.")
            return

        saved, failed = [], []
        for item in items:
            final_url = item.get("url") or (urls[0] if urls else "")
            success = self.storage.save_recommendation(
                category=item["category"],
                title=item["title"],
                context=item.get("description", ""),
                url=final_url,
                tags=item.get("tags", []),
                confidence=item.get("confidence", 0.7),
                raw_input=text,
                telegram_chat_id=update.message.chat.id,
                telegram_message_id=update.message.message_id,
                image_url=image_file_url,
                image_bytes=image_bytes,
            )
            if success:
                saved.append(item)
            else:
                failed.append(item)

        if len(saved) == 1:
            item = saved[0]
            await update.message.reply_text(
                f"✅ Рекомендация сохранена!\n"
                f"Категория: {item['category']}\n"
                f"Название: {item['title']}"
            )
        elif len(saved) > 1:
            lines = [f"✅ Сохранено {len(saved)}:"]
            for item in saved:
                lines.append(f"• {item['title']} → {item['category']}")
            if failed:
                lines.append(f"\n❌ Не удалось сохранить {len(failed)}:")
                for item in failed:
                    lines.append(f"• {item['title']}")
            await update.message.reply_text("\n".join(lines))
        else:
            await update.message.reply_text("❌ Ошибка при сохранении рекомендаций.")

    async def show_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
        """Show all items for a given category."""
        from telegram import InputMediaPhoto
        items = self.storage.get_by_category(category)
        if not items:
            await update.message.reply_text(f"Список *{category}* пуст.", parse_mode="Markdown")
            context.user_data["last_shown"] = {"category": category, "items": []}
            return
        # Save context for follow-up commands
        all_items_with_ids = self.storage.get_all_in_category(category)
        context.user_data["last_shown"] = {"category": category, "items": all_items_with_ids}
        lines = [f"*{category}* ({len(items)}):\n"]
        images = []
        for i, item in enumerate(items, 1):
            title = item.get("title", "") or "Без названия"
            url = item.get("url", "")
            image_url = item.get("image_url", "")
            if url:
                lines.append(f"{i}. [{title}]({url})")
            else:
                lines.append(f"{i}. {title}")
            if image_url:
                images.append(image_url)
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        if images:
            for i in range(0, len(images), 10):
                batch = images[i:i+10]
                try:
                    media = [InputMediaPhoto(media=img_url) for img_url in batch]
                    await update.message.reply_media_group(media=media)
                except Exception as e:
                    print(f"Error sending images: {e}")

    async def handle_bulk_add(self, update: Update, bulk: dict):
        """Save multiple items to a list category."""
        category = bulk["category"]
        items = bulk["items"]
        saved, failed = [], []
        for item in items:
            if self.storage.quick_save(category, item):
                saved.append(item)
            else:
                failed.append(item)
        lines = [f"✅ Добавлено в *{category}* ({len(saved)}):"] + [f"• {t}" for t in saved]
        if failed:
            lines += [f"\n❌ Не удалось добавить:"] + [f"• {t}" for t in failed]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def handle_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE, delete_req: dict):
        """Handle delete request."""
        action = delete_req.get("action")
        last_shown = context.user_data.get("last_shown", {})

        # Resolve category: explicit or from context
        category = delete_req.get("category") or last_shown.get("category")
        if not category:
            await update.message.reply_text("Не понятно из какого списка удалять. Сначала покажи список — например, 'покажи список продуктов'.")
            return

        if action == "clear_list":
            all_items = self.storage.get_all_in_category(category)
            if not all_items:
                await update.message.reply_text(f"Список *{category}* уже пуст.", parse_mode="Markdown")
                return
            context.user_data["pending_clear"] = {"category": category, "ids": [i["id"] for i in all_items]}
            keyboard = [[
                InlineKeyboardButton("✅ Да, удалить всё", callback_data="clear_confirm"),
                InlineKeyboardButton("❌ Отмена", callback_data="clear_cancel"),
            ]]
            await update.message.reply_text(
                f"Удалить весь список *{category}* ({len(all_items)} записей)?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif action == "delete_by_position":
            positions = delete_req.get("positions", [])
            items_in_context = last_shown.get("items", [])
            if not items_in_context:
                await update.message.reply_text("Сначала покажи список, чтобы я знала нумерацию.")
                return
            ids_to_delete = []
            deleted_titles = []
            for pos in positions:
                if 0 < pos <= len(items_in_context):
                    item = items_in_context[pos - 1]
                    ids_to_delete.append(item["id"])
                    deleted_titles.append(f"{pos}. {item['title']}")
            if not ids_to_delete:
                await update.message.reply_text("Не нашла пунктов с такими номерами.")
                return
            self.storage.delete_pages(ids_to_delete)
            lines = [f"✅ Удалено:"] + [f"• {t}" for t in deleted_titles]
            await update.message.reply_text("\n".join(lines))

        elif action == "delete_items":
            requested = delete_req.get("items", [])
            all_items = self.storage.get_all_in_category(category)
            ids_to_delete = self.categorizer.match_items_to_delete(requested, all_items)
            if not ids_to_delete:
                await update.message.reply_text("Не нашла таких записей в списке.")
                return
            deleted_titles = [item["title"] for item in all_items if item["id"] in ids_to_delete]
            count = self.storage.delete_pages(ids_to_delete)
            lines = [f"✅ Удалено {count}:"] + [f"• {t}" for t in deleted_titles]
            await update.message.reply_text("\n".join(lines))

    async def handle_clear_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Yes/No confirmation for clear_list."""
        query = update.callback_query
        await query.answer()
        if query.data == "clear_confirm":
            pending = context.user_data.get("pending_clear")
            if not pending:
                await query.edit_message_text("Не нашла что удалять — попробуй ещё раз.")
                return
            count = self.storage.delete_pages(pending["ids"])
            await query.edit_message_text(f"✅ Удалено {count} записей из *{pending['category']}*.", parse_mode="Markdown")
            context.user_data.pop("pending_clear", None)
        else:
            await query.edit_message_text("Отменено.")
            context.user_data.pop("pending_clear", None)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages."""
        # Handle pending clarification before any other checks
        if update.message.text and context.user_data.get("pending_clarification"):
            pending = context.user_data.pop("pending_clarification")
            clarified_text = f"{pending['text']}\nПояснение: {update.message.text}"
            await self._process_recommendation(
                update, context,
                clarified_text,
                pending.get("urls", []),
                pending.get("content_type", "text"),
                pending.get("image_file_url"),
                pending.get("image_bytes"),
            )
            return

        # Process all direct messages to the bot
        text = ""
        urls = []
        image_text = ""
        image_bytes = None
        image_file_url = None

        # Transcribe voice/audio to text
        text_input = update.message.text or ""
        if update.message.voice or update.message.audio:
            transcribed = await transcribe_audio(update, context)
            if not transcribed:
                await update.message.reply_text("Не удалось распознать аудио.")
                return
            text_input = transcribed
            await update.message.reply_text(f"🎤 Распознано: {transcribed}")

        # Check for delete/show/add commands
        if text_input:
            msg = text_input.lower()
            last_shown = context.user_data.get("last_shown", {})

            delete_triggers = ["удали", "удалить", "вычеркни", "уже купила", "уже купил", "уже сделала", "уже сделал", "очисти", "убери"]
            add_triggers = ["добавь", "добавить", "добавляй", "купи ", "купить "]

            if any(t in msg for t in delete_triggers):
                delete_req = self.categorizer.identify_delete_request(text_input)
                if delete_req:
                    await self.handle_delete(update, context, delete_req)
                    return

            if any(t in msg for t in add_triggers) or (last_shown.get("category") and ("," in msg or "\n" in msg)):
                context_category = last_shown.get("category")
                bulk = self.categorizer.identify_bulk_add(text_input, context_category)
                if bulk:
                    await self.handle_bulk_add(update, bulk)
                    return

            if "покажи" in msg or "что " in msg:
                category = self.categorizer.identify_show_category(text_input)
                if category:
                    await self.show_category(update, context, category)
                    return

        # Process text message
        if text_input:
            text = text_input
            urls.extend(self.extract_urls(text))

        # Process image (screenshot)
        image_bytes = None
        if update.message.photo:
            try:
                image_text, image_bytes = await process_image_message(update, context)
                if image_text:
                    text = f"{text}\n{image_text}".strip() if text else image_text
                    urls.extend(self.extract_urls(image_text))

                # Get Telegram file URL for the image
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                image_file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file.file_path}"
            except Exception as e:
                print(f"Error processing image: {e}")
                image_file_url = None

        # Process caption if image has one
        if update.message.caption:
            caption = update.message.caption
            text = f"{text}\n{caption}".strip() if text else caption
            urls.extend(self.extract_urls(caption))

        # Deduplicate URLs while preserving order
        urls = list(dict.fromkeys(urls))

        # If no text extracted, skip
        if not text or not text.strip():
            await update.message.reply_text("Не удалось извлечь текст из сообщения.")
            return

        # Determine content type
        if image_bytes:
            content_type = "image_with_text" if update.message.caption else "image"
        elif urls:
            content_type = "link"
        else:
            content_type = "text"

        try:
            await self._process_recommendation(update, context, text, urls, content_type, image_file_url, image_bytes)
        except Exception as e:
            print(f"Error processing recommendation: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    def run(self):
        """Run the bot."""
        try:
            application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            
            application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO, self.handle_message))
            application.add_handler(CallbackQueryHandler(self.handle_clear_callback, pattern="^clear_"))

            print("Bot is running...")
            print("Press Ctrl+C to stop the bot.")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True  # Ignore old updates
            )
        except KeyboardInterrupt:
            print("\n\nBot stopped by user.")
        except Exception as e:
            error_msg = str(e)
            if "InvalidToken" in error_msg or "token" in error_msg.lower():
                print("\n❌ Ошибка: Неверный токен Telegram бота!")
                print("   Проверьте, что TELEGRAM_BOT_TOKEN в файле .env установлен правильно.")
            else:
                print(f"\n❌ Ошибка при запуске бота: {e}")
                import traceback
                traceback.print_exc()
            raise


if __name__ == "__main__":
    # Validate configuration before starting
    validate_config()
    
    bot = RecommendationBot()
    bot.run()

