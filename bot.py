"""Main Telegram bot for processing recommendations."""
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, validate_config
from image_processor import process_image_message
from llm_categorizer import LLMCategorizer
from storage_factory import get_storage


class RecommendationBot:
    def __init__(self):
        self.categorizer = LLMCategorizer()
        self.storage = get_storage()

    def extract_url(self, text: str) -> str:
        """Extract URL from text."""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        match = url_pattern.search(text)
        return match.group(0) if match else ""

    async def show_category(self, update: Update, category: str):
        """Show all items for a given category."""
        from telegram import InputMediaPhoto
        items = self.storage.get_by_category(category)
        if not items:
            await update.message.reply_text(f"Список *{category}* пуст.", parse_mode="Markdown")
            return
        lines = [f"*{category}* ({len(items)}):\n"]
        images = []
        for item in items:
            title = item.get("title", "") or "Без названия"
            url = item.get("url", "")
            image_url = item.get("image_url", "")
            if url:
                lines.append(f"• [{title}]({url})")
            else:
                lines.append(f"• {title}")
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

    async def handle_delete(self, update: Update, delete_req: dict):
        """Handle delete request."""
        action = delete_req.get("action")
        category = delete_req.get("category")

        if action == "clear_list":
            all_items = self.storage.get_all_in_category(category)
            if not all_items:
                await update.message.reply_text(f"Список *{category}* уже пуст.", parse_mode="Markdown")
                return
            count = self.storage.delete_pages([item["id"] for item in all_items])
            await update.message.reply_text(f"✅ Удалено {count} записей из *{category}*.", parse_mode="Markdown")

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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages."""
        # Process all direct messages to the bot
        text = ""
        url = ""
        image_text = ""
        image_bytes = None
        image_file_url = None

        # Check for delete/show commands
        if update.message.text:
            msg = update.message.text.lower()
            delete_triggers = ["удали", "удалить", "вычеркни", "уже купила", "уже купил", "уже сделала", "уже сделал", "очисти", "убери"]
            if any(t in msg for t in delete_triggers):
                delete_req = self.categorizer.identify_delete_request(update.message.text)
                if delete_req:
                    await self.handle_delete(update, delete_req)
                    return
            if "покажи" in msg or "список" in msg or "что " in msg:
                category = self.categorizer.identify_show_category(update.message.text)
                if category:
                    await self.show_category(update, category)
                    return

        # Process text message
        if update.message.text:
            text = update.message.text
            url = self.extract_url(text)

        # Process image (screenshot)
        image_bytes = None
        if update.message.photo:
            try:
                image_text, image_bytes = await process_image_message(update, context)
                if image_text:
                    text = f"{text}\n{image_text}".strip() if text else image_text
                    # Try to extract URL from image text
                    if not url:
                        url = self.extract_url(image_text)
                
                # Get Telegram file URL for the image
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                # Construct full URL to Telegram file
                image_file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file.file_path}"
            except Exception as e:
                print(f"Error processing image: {e}")
                image_file_url = None

        # Process caption if image has one
        if update.message.caption:
            caption = update.message.caption
            text = f"{text}\n{caption}".strip() if text else caption
            if not url:
                url = self.extract_url(caption)

        # If no text extracted, skip
        if not text or not text.strip():
            await update.message.reply_text("Не удалось извлечь текст из сообщения.")
            return

        # Store raw input
        raw_input = text
        
        # Determine content type
        if image_bytes:
            if update.message.caption:
                content_type = "image_with_text"
            else:
                content_type = "image"
        elif url:
            content_type = "link"
        else:
            content_type = "text"
        
        # Categorize using LLM
        try:
            result = self.categorizer.categorize(text, url, content_type)
            
            # Use extracted URL if available, otherwise use URL from LLM result
            final_url = url if url else result.get("url", "")
            
            # Save to storage
            success = self.storage.save_recommendation(
                category=result["category"],
                title=result["title"],
                context=result.get("description", ""),
                url=final_url,
                tags=result.get("tags", []),
                confidence=result.get("confidence", 0.7),
                raw_input=raw_input,
                telegram_chat_id=update.message.chat.id,
                telegram_message_id=update.message.message_id,
                image_url=image_file_url,
                image_bytes=image_bytes
            )

            if success:
                await update.message.reply_text(
                    f"✅ Рекомендация сохранена!\n"
                    f"Категория: {result['category']}\n"
                    f"Название: {result['title']}"
                )
            else:
                await update.message.reply_text("❌ Ошибка при сохранении рекомендации.")
        except Exception as e:
            print(f"Error processing recommendation: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    def run(self):
        """Run the bot."""
        try:
            application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Add handler for all messages
            application.add_handler(
                MessageHandler(
                    filters.TEXT | filters.PHOTO,
                    self.handle_message
                )
            )

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

