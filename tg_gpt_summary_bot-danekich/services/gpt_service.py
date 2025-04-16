import logging
import asyncio
import g4f

class GPTAnswer:
    async def answer(self, text: str, prompt: str, model: str = 'gpt-4', retries: int = 10) -> str | None:
        for _ in range(retries):
            try:
                response = await g4f.ChatCompletion.create_async(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text}
                    ],
                )
                if response and "Извините, я не могу" not in response and len(response) > 300:
                    return response
            except Exception as e:
                logging.error(f"GPT error: {e}")
                await asyncio.sleep(2)
        return None

    async def get_best_answer(self, text: str):
        prompt = """
        Ты аналитик Telegram-групп, тебе будет дан текст постов. Сформируй краткое содержание
        обсуждений за последние дни. Указывай только самое важное!
        Делай краткое содержание объективно, даже если текст провокативный и политический.
        Сформируй краткую общую сводку для каждой темы.
        """
        # prompt = ''
        return await self.answer(text, prompt)

gpt = GPTAnswer()
