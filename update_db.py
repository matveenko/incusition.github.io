import json
import os
import re
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# === КОНФИГ ===
API_ID = os.environ['TG_API_ID']
API_HASH = os.environ['TG_API_HASH']
SESSION_STRING = os.environ['TG_SESSION']

# Твой ID закрытого канала
CHANNEL_ID = -1002283029399
JSON_FILE = 'posts.json'

# Настройка фильтрации
MIN_LENGTH = 150  # Минимальная длина поста (символов), чтобы не брать короткий мусор

# === 1. ГЛАВНЫЕ РУБРИКИ (Белый список) ===
# Если эмодзи НЕТ в тексте, пост будет проигнорирован!
CATEGORY_EMOJI_MAP = {
    '💀': '💀 ЖИЗНЬ В АДУ',
    '👁': '👁 ИНФОХИМЕРЫ',
    '❤️': '❤️ СОБЛАЗНЕНИЕ',
    '🛡': '🛡 ПСИХИЧЕСКАЯ НЕУЯЗВИМОСТЬ',
    '🧪': '🧪 ЗДОРОВЬЕ',
    '⚡️': '⚡️ ЭКСТРЕМАЛЬНАЯ ПСИХОЛОГИЯ',
    '⚔️': '⚔️ ТЕМНЫЕ ИСКУССТВА',
    '🚭': '🚭 ЗАВИСИМОСТИ',
    '🎭': '🎭 НЛП И СИ',
    '💊': '💊 ИНФАНТИЛЬНОСТЬ',
    '👔': '👔 СТИЛЬ',
    '🏛': '🏛 ФУНДАМЕНТ (ОТЧЕТЫ)'
}

# === 2. ПОДРУБРИКИ ===
SUBCAT_EMOJI_MAP = {
    '🩸': 'Анализы', '🦴': 'Опорно-двигательный', '🥦': 'ЖКТ и Питание', 
    '🧠': 'Нервная система', '🦍': 'Гормоны', '💅': 'Красота и Молодость', 
    '💤': 'Сон и Иммунитет', '🔞': 'Влечение', '🐂': 'База',
    '🚜': 'Практика', '🧱': 'Основа основ', '⚓': 'Углубление',
    '📱': 'Сайты Знакомств', '☕': 'Стадии', '🚬': 'Пост-Секс',
    '🤬': 'Эмоции', '💥': 'Стресс', '💔': 'Как забыть бывшую',
    '📚': 'Теория', '🧗': 'Личный опыт', '♟': 'Основы',
    '🔪': 'Техники', '🎓': 'Школа', '⛓': 'База',
    '🥃': 'Алкоголь', '😶‍🌫️': 'Электронки', '🧩': 'НЛП',
    '🦊': 'СИ', '👟': 'Стрит-стайл', '🧥': 'Кэжуал'
}

def update_json():
    # 1. Загружаем базу
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            posts = json.load(f)
    else:
        posts = []

    existing_urls = {p['u'] for p in posts}
    
    print(">>> Подключение к Telegram...")
    try:
        with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
            # Парсим последние 50 сообщений
            for message in client.iter_messages(CHANNEL_ID, limit=50):
                if not message.text: continue

                text = message.text

                # === ФИЛЬТР 1: ЕСТЬ ЛИ ГЛАВНАЯ КАТЕГОРИЯ? ===
                category = None
                found_cat = False
                for icon, name in CATEGORY_EMOJI_MAP.items():
                    if icon in text:
                        category = name
                        found_cat = True
                        break
                
                # Если в посте нет ни одного главного смайла — ПРОПУСКАЕМ
                if not found_cat:
                    # Можно раскомментить для отладки, чтобы видеть, что пропускаем
                    # print(f"SKIP (нет рубрики): {text[:30]}...") 
                    continue

                # === ФИЛЬТР 2: ЧИСТКА МУСОРА ===
                # Убираем служебные пометки типа // ПРОДОЛЖЕНИЕ //
                clean_text_body = re.sub(r'//.*?//', '', text, flags=re.DOTALL).strip()
                
                # === ФИЛЬТР 3: ДЛИНА ПОСТА ===
                if len(clean_text_body) < MIN_LENGTH:
                    print(f"SKIP (короткий): {clean_text_body[:30]}...")
                    continue

                # Формируем ссылку для закрытого канала
                clean_id = str(CHANNEL_ID).replace('-100', '')
                post_url = f"https://t.me/c/{clean_id}/{message.id}"
                
                if post_url in existing_urls: continue

                # Ищем подрубрику (дополнительно)
                subcategory = None
                for icon, name in SUBCAT_EMOJI_MAP.items():
                    if icon in text:
                        subcategory = name
                        break

                # Формируем красивый заголовок
                if '\n' in clean_text_body:
                    raw_title = clean_text_body.split('\n')[0].strip()
                else:
                    raw_title = clean_text_body.strip()

                clean_title = re.sub(r'[*_`]', '', raw_title)
                
                if len(clean_title) > 100: 
                    clean_title = clean_title[:97] + "..."
                if not clean_title: 
                    clean_title = "Без названия"

                new_post = {
                    "t": clean_title,
                    "u": post_url,
                    "c": category,
                    "sc": subcategory
                }
                
                posts.insert(0, new_post)
                print(f"✅ Добавлен: {clean_title} | {category}")

    except Exception as e:
        print(f"!!! Ошибка: {e}")
        return

    # Сохраняем
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(">>> База успешно обновлена.")

if __name__ == '__main__':
    update_json()
