import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        # Можешь писать сюда любые сырые SQL запросы
        await db.execute(text("DELETE FROM price_results;"))
        await db.commit()
        print("🧹 Таблица price_results успешно очищена!")

if __name__ == "__main__":
    asyncio.run(main())