"""
Скрипт очистки поврежденных долларовых цен FunPay (< 45 руб)
и мгновенного перепарсинга актуальных цен для Palworld.
"""
from database import SyncSessionLocal
from models import PriceResult
from services.parsers.funpay import parse_funpay
from worker import save_prices

def main():
    db = SyncSessionLocal()
    try:
        # 1. Удаляем аномальные цены FunPay (< 45 руб, попавшие в базу из-за долларовой выдачи)
        deleted_count = (
            db.query(PriceResult)
            .filter(PriceResult.shop_name.like("FunPay%"), PriceResult.price < 45.0)
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"Удалено {deleted_count} аномальных долларовых цен FunPay (< 45 руб).")

        # 2. Перепарсиваем свежие рублевые цены для Palworld (id=2)
        fresh_palworld = parse_funpay(2, "https://funpay.com/lots/2167/", game_name="Palworld")
        if fresh_palworld:
            save_prices(fresh_palworld)
            print(f"Успешно обновлено {len(fresh_palworld)} актуальных цен FunPay для Palworld.")
            for o in fresh_palworld:
                print(f"  {o['shop_name']}: {o['price']} ₽ ({o['lot_url']})")
    finally:
        db.close()

if __name__ == "__main__":
    main()
