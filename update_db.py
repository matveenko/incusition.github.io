import json
import os
import re
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# === КОНФИГ ===
API_ID = os.environ['TG_API_ID']
API_HASH = os.environ['TG_API_HASH']
SESSION_STRING = os.environ['TG_SESSION']

CHANNEL_ID = -1002283029399
JSON_FILE = 'posts.json'
MIN_LENGTH = 250

# === 1. ГЛАВНЫЕ РУБРИКИ ===
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

def clean_markdown(text):
    return re.sub(r'[*_`\[\]]', '', text).strip()

def get_title_from_text(text):
    """Берет первую строку, которая не является названием рубрики"""
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Проверяем, не является ли строка названием рубрики
        is_category_name = False
        for cat_name in CATEGORY_EMOJI_MAP.values():
            if cat_name in line or line in cat_name:
                is_category_name = True
                break
        
        if not is_category_name:
            return clean_markdown(line)
    return "Без названия"

def update_json():
    # 1. Загрузка базы
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            posts = json.load(f)
    else:
        posts = []

    existing_urls = {p['u'] for p in posts}
    
    # Список новых обработанных постов
    new_posts_buffer = []

    print(">>> Подключение к Telegram...")
    try:
        with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
            
            # Получаем последние 50 сообщений
            messages = list(client.iter_messages(CHANNEL_ID, limit=50))
            
            # ВАЖНО: Разворачиваем список, чтобы идти от СТАРЫХ к НОВЫМ
            # Это нужно, чтобы сначала обработать "Часть 1", запомнить её заголовок,
            # и применить его к "Часть 2".
            messages.reverse()

            # Контекст для цепочек постов
            context = {
                "active_title": None,
                "active_category": None,
                "active_subcategory": None,
                "part_counter": 2 # Следующая часть будет второй
            }

            for message in messages:
                if not message.text: continue
                
                text = message.text
                
                # Проверяем, является ли пост ПРОДОЛЖЕНИЕМ
                # Регулярка ищет "// продолжение поста //" (регистронезависимо)
                continuation_pattern = r'//\s*продолжение\s*поста\s*//'
                is_continuation = re.search(continuation_pattern, text, flags=re.IGNORECASE)

                final_title = ""
                final_category = None
                final_subcategory = None
                clean_text_body = ""

                if is_continuation:
                    # === ЛОГИКА ПРОДОЛЖЕНИЯ ===
                    # Вырезаем метку продолжения
                    clean_text_body = re.sub(continuation_pattern, '', text, flags=re.IGNORECASE).strip()
                    
                    # Если у нас есть сохраненный контекст от предыдущего поста
                    if context["active_title"]:
                        final_title = f"{context['active_title']} (ч.{context['part_counter']})"
                        final_category = context["active_category"]
                        final_subcategory = context["active_subcategory"]
                        
                        # Увеличиваем счетчик для возможной 3-й части
                        context["part_counter"] += 1
                    else:
                        # Если попался пост-продолжение, а начала мы не видели (например, оно было давно)
                        final_title = get_title_from_text(clean_text_body) + " (Продолжение)"
                        final_category = "Неизвестно" # Или можно поставить null
                
                else:
                    # === ЛОГИКА НОВОГО ПОСТА ===
                    # 1. Ищем категорию (обязательно для начала цепочки)
                    found_cat = False
                    found_cat_name = None
                    for icon, name in CATEGORY_EMOJI_MAP.items():
                        if icon in text:
                            found_cat_name = name
                            found_cat = True
                            break
                    
                    # Если это не продолжение и нет категории — пропускаем (реклама, щитпост)
                    if not found_cat:
                        # Сбрасываем контекст, так как цепочка прервалась левым постом
                        context["active_title"] = None
                        continue

                    # 2. Чистим текст
                    clean_text_body = re.sub(r'//.*?//', '', text, flags=re.DOTALL).strip()
                    
                    # 3. Определяем заголовок
                    base_title = get_title_from_text(clean_text_body)
                    
                    # 4. Ищем подрубрику
                    found_subcat = None
                    for icon, name in SUBCAT_EMOJI_MAP.items():
                        if icon in text:
                            found_subcat = name
                            break

                    # 5. ОБНОВЛЯЕМ КОНТЕКСТ (запоминаем этот пост как Родителя)
                    context["active_title"] = base_title
                    context["active_category"] = found_cat_name
                    context["active_subcategory"] = found_subcat
                    context["part_counter"] = 2 # Сброс счетчика
                    
                    final_title = base_title
                    final_category = found_cat_name
                    final_subcategory = found_subcat

                # === ОБЩИЕ ПРОВЕРКИ ===
                if len(clean_text_body) < MIN_LENGTH: continue

                # Формируем URL
                clean_id = str(CHANNEL_ID).replace('-100', '')
                post_url = f"https://t.me/c/{clean_id}/{message.id}"
                
                if post_url in existing_urls: continue

                # Обрезаем длинный заголовок
                if len(final_title) > 100: 
                    final_title = final_title[:97] + "..."

                new_post = {
                    "t": final_title,
                    "u": post_url,
                    "c": final_category,
                    "sc": final_subcategory
                }
                
                new_posts_buffer.append(new_post)
                print(f"✅ Обработан: {final_title} [{final_category}]")

    except Exception as e:
        print(f"!!! Ошибка: {e}")
        return

    # Добавляем новые посты в начало общего списка (но в обратном порядке буфера, чтобы новые были сверху)
    # new_posts_buffer сейчас от Старых к Новым. 
    # Нам нужно вставить их в начало JSON файла, где 0 индекс = самый новый.
    # Поэтому разворачиваем buffer обратно.
    for p in reversed(new_posts_buffer):
        posts.insert(0, p)

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(">>> База успешно обновлена.")

if __name__ == '__main__':
    update_json()
