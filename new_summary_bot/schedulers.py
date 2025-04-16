from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from aiogram import Bot
from sqlalchemy import select
from config import BOT_TOKEN
from database import async_session
from models import User, Post
from services.gpt_summary import generate_summary
import pytz
import logging
from aiogram.client.default import DefaultBotProperties

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
scheduler = AsyncIOScheduler()

UTC = pytz.UTC

async def daily_summary_job():
    """
    Раз в минуту проходимся по всем пользователям.
    С учётом user_offset вычисляем, который сейчас час у пользователя,
    и если совпадает с его schedule_time, отправляем дайджест.
    """
    now_utc = datetime.utcnow().replace(tzinfo=UTC)
    # Пройдёмся по всем пользователям
    async with async_session() as session:
        users = (await session.execute(select(User))).scalars().all()

        for user in users:
            if not user.schedule_time:
                continue  # не задано время

            # Парсим user.schedule_time (HH:MM)
            try:
                hh_str, mm_str = user.schedule_time.split(":")
                user_hh = int(hh_str)
                user_mm = int(mm_str)
            except:
                continue

            # Прибавляем offset (если user_offset = +3, значит локальное время +3 к UTC)
            # Для упрощения допустим offset — целое число часов
            user_local_time_now = now_utc + timedelta(hours=user.user_offset)
            # Если локальное время совпадает с schedule_time (поминам только HH:MM)
            if user_local_time_now.hour == user_hh and user_local_time_now.minute == user_mm:
                # Проверяем, не отправляли ли уже сегодня
                last_sent_utc = user.last_summary_sent
                if last_sent_utc:
                    # Переводим last_sent_utc -> локальное
                    last_sent_local = last_sent_utc + timedelta(hours=user.user_offset)
                    if (last_sent_local.date() == user_local_time_now.date()):
                        continue  # уже отправляли сегодня

                # Собираем посты за сутки
                day_ago = now_utc - timedelta(days=1)
                posts = (await session.execute(
                    select(Post).where(
                        Post.user_id == user.id,
                        Post.date > day_ago
                    )
                )).scalars().all()
                if not posts:
                    continue

                posts_for_gpt = []
                for p in posts:
                    posts_for_gpt.append({
                        "channel": p.channel_tag,
                        "text": p.text or "",
                        "link": p.link or ""
                    })

                summary_text = await generate_summary(posts_for_gpt)
                # Посчитаем время чтения
                # Для демонстрации: возьмём длину всех текстов, etc.
                total_chars = 0
                for p in posts_for_gpt:
                    total_chars += len(p["text"])
                original_read_secs = int(total_chars / 1000 * 60)  # CHARS_PER_MIN=1000
                summary_read_secs = int(len(str(summary_text)) / 1000 * 60)

                saved_secs = original_read_secs - summary_read_secs

                msg_text = (
                    f"<b>Ежедневный дайджест</b>\n\n"
                    f"{summary_text}\n\n"
                    f"Всего постов: {len(posts_for_gpt)}\n"
                    f"Время на чтение оригинала: ~{original_read_secs} сек.\n"
                    f"Время на чтение саммари: ~{summary_read_secs} сек.\n"
                    f"Сэкономлено: ~{saved_secs} сек."
                )
                try:
                    await bot.send_message(user.telegram_id, msg_text)
                    user.last_summary_sent = now_utc  # обновляем UTC-время
                    session.add(user)
                    logger.info(f"Отправлен дайджест пользователю {user.telegram_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке дайджеста user {user.telegram_id}: {e}")

        await session.commit()

def setup_scheduler():
    scheduler.add_job(daily_summary_job, "cron", minute="*")
    scheduler.start()
