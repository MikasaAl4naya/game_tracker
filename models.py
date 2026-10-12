from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class GameCatalog(Base):
    __tablename__ = "games_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    url_funpay = Column(String, nullable=True)

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
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    game = relationship("GameCatalog", back_populates="prices")
