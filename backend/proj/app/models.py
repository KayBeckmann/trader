from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
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

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    type = Column(Enum('long', 'short', name='trade_type'), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    status = Column(Enum('open', 'closed', name='trade_status'), default='open', nullable=False)
    result = Column(Integer) # 1 for win, -1 for loss, 0 for neutral
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed_at = Column(DateTime)

class KNNResult(Base):
    __tablename__ = "knn_results"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    type = Column(Enum('long', 'short', name='knn_result_type'), nullable=False)
    rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=True)  # Confidence score from ML model
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

