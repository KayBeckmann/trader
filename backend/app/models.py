from sqlalchemy import Column, Integer, String, Float, DateTime
from .database import Base
import datetime

class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class SymbolFailure(Base):
    __tablename__ = "symbol_failures"

    symbol = Column(String, primary_key=True, index=True)
    failure_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
