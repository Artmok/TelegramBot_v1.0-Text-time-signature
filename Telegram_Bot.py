import asyncio
import os
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, CallbackContext
import requests
from deep_translator import GoogleTranslator
import deepl
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz

# Чутливі дані тепер зчитуються з змінних середовища
TOKEN = os.getenv("TELEGRAM_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
DEEPL_KEY = os.getenv("DEEPL_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Створюємо інстанс бота
bot = Bot(token=TOKEN)

# Ініціалізація змінної для зберігання опублікованих новин
published_news = set()

# Функція для перекладу тексту за допомогою DeepL API
def translate_text_deepl(text, target_language="uk"):
    try:
        translator = deepl.Translator(DEEPL_KEY)
        result = translator.translate_text(text, target_lang=target_language)
        return result.text
    except Exception as e:
        print(f"Помилка під час перекладу: {e}")
        return text  # Якщо переклад не вдався, повертаємо оригінальний текст

# Додаємо підпис до кожної новини
def add_signature(message):
    signature = "\n\nЗавжди свіжі ігрові новини на:\n[🇺🇦AGC](https://t.me/Artmok_GC)"
    return f"{message}{signature}"

# Функція для отримання новин з RSS і публікації в канал
async def post_rss_news_to_channel():
    global published_news  # Використовуємо глобальну змінну

    try:
        rss_url = "https://feeds.feedburner.com/ign/pc-articles"
        response = requests.get(rss_url)
        soup = BeautifulSoup(response.content, 'xml')
        articles = soup.find_all('item')

        new_news = []

        for article in articles:
            title = article.title.text
            link = article.link.text
            description = article.description.text

            # Використовуємо посилання як унікальний ідентифікатор
            if link not in published_news:
                # Переклад за допомогою DeepL
                translated_title = translate_text_deepl(title, "uk")
                translated_description = translate_text_deepl(description, "uk")

                # Додаємо підпис
                message = f"*{translated_title}*\n\n{translated_description}\n[Читати далі]({link})"
                message_with_signature = add_signature(message)

                await bot.send_message(chat_id=CHANNEL_ID, text=message_with_signature, parse_mode="Markdown")

                # Додаємо новину до списку опублікованих
                published_news.add(link)
                new_news.append(title)

                # Пауза між відправленнями новин
                await asyncio.sleep(7200)

        # Якщо не знайдено нових новин
        if not new_news:
            print("Нові новини не знайдено.")
        else:
            print(f"Нові новини: {new_news}")

    except Exception as e:
        print(f"Помилка під час отримання новин або публікації з RSS: {e}")

# Функція для перевірки, чи зараз у діапазоні часу між 10:00 та 22:00 за Київським часом
def is_within_posting_hours():
    kyiv_tz = pytz.timezone("Europe/Kiev")
    now = datetime.now(kyiv_tz).time()
    start_time = datetime.strptime("10:00", "%H:%M").time()
    end_time = datetime.strptime("22:00", "%H:%M").time()
    return start_time <= now <= end_time

# Основна функція для планування публікації новин
async def schedule_news():
    while True:
        if is_within_posting_hours():
            print("Час публікації новин.")
            await post_rss_news_to_channel()
            await asyncio.sleep(7200)  # Публікуємо кожні 2 години (7200 секунд)
        else:
            print("Зараз не час для публікації новин.")
            await asyncio.sleep(600)  # Перевіряємо кожні 10 хвилин, чи настав час публікації

# Основна функція для запуску бота
def main():
    app = Application.builder().token(TOKEN).build()

    # Запускаємо планувальник новин
    loop = asyncio.get_event_loop()
    loop.create_task(schedule_news())

    # Запускаємо бота
    app.run_polling()

if __name__ == '__main__':
    main()
