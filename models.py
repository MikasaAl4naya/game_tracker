from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class GameCatalog(Base):
    __tablename__ = "games_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    url_funpay = Column(String, nullable=True)
    steam_appid = Column(Integer, nullable=True)
    steamspy_owners = Column(Integer, nullable=True)
    is_free = Column(Boolean, nullable=True)

    tasks = relationship("UserTask", back_populates="game")
    prices = relationship("PriceResult", back_populates="game")


class UserTask(Base):
    __tablename__ = "user_tasks"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games_catalog.id"), index=True)
    target_price = Column(Float)
    chat_id = Column(BigInteger)

    game = relationship("GameCatalog", back_populates="tasks")


class PriceResult(Base):
    __tablename__ = "price_results"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games_catalog.id"), index=True)
    shop_name = Column(String)
    price = Column(Float)
    lot_name = Column(String)
    lot_url = Column(String)
    region = Column(String, default="Unknown")
    platform = Column(String, default="Steam", index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    game = relationship("GameCatalog", back_populates="prices")


class DonateGame(Base):
    __tablename__ = "donate_games"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    publisher = Column(String)
    icon_url = Column(String)
    banner_url = Column(String)
    currency_name = Column(String)
    id_type = Column(String, default="UID")  # UID, Riot ID, Username, Player ID
    is_popular = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    packages = relationship("DonatePackage", back_populates="game", cascade="all, delete-orphan", order_by="DonatePackage.sort_order")


class DonatePackage(Base):
    __tablename__ = "donate_packages"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("donate_games.id", ondelete="CASCADE"), index=True)
    package_type = Column(String, default="currency")  # currency, subscription, pass
    name = Column(String)
    amount = Column(Integer, default=0)
    bonus = Column(Integer, default=0)
    icon = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)

    game = relationship("DonateGame", back_populates="packages")
    offers = relationship("DonateOffer", back_populates="package", cascade="all, delete-orphan", order_by="DonateOffer.price")


class DonateOffer(Base):
    __tablename__ = "donate_offers"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("donate_packages.id", ondelete="CASCADE"), index=True)
    shop_name = Column(String, index=True)
    price = Column(Float)
    original_price = Column(Float, nullable=True)
    delivery_type = Column(String, default="uid")  # uid (по UID), login (вход), code (код)
    delivery_time = Column(String, default="1-3 мин")
    payment_methods = Column(String, default="СБП, Карты РФ")
    rating = Column(Float, default=4.9)
    reviews_count = Column(Integer, default=1000)
    promo_code = Column(String, nullable=True)
    promo_discount = Column(String, nullable=True)
    url = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)

    package = relationship("DonatePackage", back_populates="offers")
