import json
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# =================== Парсинг з Foxtrot =======================
def parse_lg_tvs():
    url = "https://www.foxtrot.com.ua/uk/shop/televizory-lg.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    items = soup.select(".card__body")
    tvs = {}

    for item in items:
        title_tag = item.select_one(".card__title")
        if not title_tag:
            continue

        name = title_tag.get_text(strip=True).lower()
        url = "https://www.foxtrot.com.ua" + title_tag.get("href")

        price_tag = item.select_one(".card__price-final")
        price = price_tag.get_text(strip=True) if price_tag else "Н/Д"

        desc_tag = item.select_one(".card__description")
        desc = desc_tag.get_text(strip=True) if desc_tag else ""

        tvs[name] = {
            "назва": name.upper(),
            "посилання": url,
            "ціна": price,
            "опис": desc
        }

    return tvs

# =============== Telegram Bot ============================

user_state = {}
cached_tvs = {}  # Кеш для швидкої відповіді

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Пошук моделі LG", callback_data="search")],
        [InlineKeyboardButton("📥 Оновити базу", callback_data="refresh")]
    ]
    await update.message.reply_text("Привіт! Я бот LG-TV з Foxtrot 🛒. Обери дію:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "search":
        user_state[user_id] = "awaiting_model"
        await query.message.reply_text("Введіть назву моделі телевізора LG (наприклад: 55UQ75006LF):")
    elif query.data == "refresh":
        global cached_tvs
        cached_tvs = parse_lg_tvs()
        await query.message.reply_text(f"🔄 Базу оновлено. Знайдено {len(cached_tvs)} моделей LG.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message.text.lower()

    if user_state.get(user_id) == "awaiting_model":
        user_state.pop(user_id)
        if not cached_tvs:
            cached_tvs.update(parse_lg_tvs())

        found = None
        for key, tv in cached_tvs.items():
            if message in key:
                found = tv
                break

        if found:
            text = (
                f"📺 <b>{found['назва']}</b>\n"
                f"💰 Ціна: {found['ціна']}\n"
                f"📄 Опис: {found['опис'] or 'Немає'}\n"
                f"🔗 [Перейти до товару]({found['посилання']})"
            )
            await update.message.reply_html(text, disable_web_page_preview=False)
        else:
            await update.message.reply_text("❌ Модель не знайдена. Спробуйте ще раз.")
    else:
        await update.message.reply_text("Натисніть /start або скористайтесь кнопками.")

def main():
    import os
TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Бот запущено")
    app.run_polling()

if __name__ == "__main__":
    main()
