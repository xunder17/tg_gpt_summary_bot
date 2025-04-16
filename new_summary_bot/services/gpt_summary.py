import g4f
import logging
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

CHARS_PER_MIN = 1000  # Примерная скорость чтения

def calculate_reading_time(text: str) -> int:
    """
    Расчет времени чтения текста (в секундах).
    """
    chars_count = len(text)
    mins = chars_count / CHARS_PER_MIN
    return int(mins * 60)

async def generate_summary(posts, user_themes=None, retries=3):
    """
    Суммаризация списка постов с кластеризацией и GPT-обработкой.
    posts = [{"channel": "...", "text": "...", "link": "..."}...]
    user_themes = список тем (опционально).
    retries = кол-во повторов при ошибке GPT.
    """

    if not posts:
        return "Нет постов для суммаризации."

    # Урезаем длинные тексты до 500 символов
    truncated_posts = []
    for p in posts:
        text_ = p["text"]
        if len(text_) > 500:
            text_ = text_[:500] + "..."
        truncated_posts.append({
            "channel": p["channel"],
            "text": text_,
            "link": p["link"]
        })

    # Векторизация текстов и вычисление матрицы схожести
    texts = [p["text"] for p in truncated_posts]
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(texts)
    sim_matrix = (X * X.T).toarray()  # Косинусная матрица

    threshold = 0.3  # Порог схожести для объединения в кластеры
    n = len(truncated_posts)
    visited = [False] * n
    clusters = []

    def bfs(start_idx):
        queue = [start_idx]
        cluster = []
        visited[start_idx] = True
        while queue:
            idx = queue.pop(0)
            cluster.append(idx)
            for j in range(n):
                if not visited[j] and sim_matrix[idx, j] >= threshold:
                    visited[j] = True
                    queue.append(j)
        return cluster

    for i in range(n):
        if not visited[i]:
            clusters.append(bfs(i))

    # Формируем промпт для GPT
    prompt_parts = [
        "Ниже приведены сообщения, сгруппированные по смысловой схожести.",
        "Сформируй краткую общую сводку для каждой темы.",
        "Укажи ссылки на все источники, упомянутые в кластере."
    ]

    if user_themes:
        prompt_parts.append(f"Пользователь указал интересующие темы: {', '.join(user_themes)}.")

    for idx, cluster_indices in enumerate(clusters[:10], start=1):
        prompt_parts.append(f"\n🧩 Кластер {idx}:")
        for i in cluster_indices:
            post = truncated_posts[i]
            prompt_parts.append(
                f"- <b>{post['channel']}</b>: {post['text']} (ссылка: {post['link']})"
            )

    prompt_parts.append("\nОформи вывод красиво, по темам, с заголовками и короткими сводками.")

    full_prompt = "\n".join(prompt_parts)

    # Повторные попытки при ошибках GPT
    for _ in range(retries):
        try:
            print(f"gpt {_}")
            response = await g4f.ChatCompletion.create_async(
                model='gpt-4',
                messages=[
                    {"role": "system", "content": full_prompt+"\n Текст должен быть НЕ ДЛИННЕЕ 2096 символов!!! Если не хватает места под текст, распиши только самые важные темы текста"},
                    {"role": "user", "content": full_prompt+"\n Текст должен быть НЕ ДЛИННЕЕ 2096 символов!!! Если не хватает места под текст, распиши только самые важные темы текста"}
                ],
            )
            if response and "Извините, я не могу" not in response:
                print(response)
                return response[:4000]
        except Exception as e:
            logging.error(f"GPT error: {e}")
    return "❌ Не удалось сгенерировать сводку. Попробуйте позже."
