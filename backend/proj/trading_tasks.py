from .celery import app
from .app.database import SessionLocal
from .app.models import StockPrice, Trade, KNNResult
from sqlalchemy import func, desc
import datetime
import random

@app.task
def open_trades():
    db = SessionLocal()
    
    # Get the most recent timestamp from stock_prices
    latest_timestamp = db.query(func.max(StockPrice.timestamp)).scalar()
    
    if not latest_timestamp:
        print("No stock prices found to open trades.")
        db.close()
        return

    # Get all stock prices for the latest timestamp
    latest_prices = db.query(StockPrice).filter(StockPrice.timestamp == latest_timestamp).all()

    for stock_price in latest_prices:
        # Create a long trade
        long_trade = Trade(
            symbol=stock_price.symbol,
            type='long',
            entry_price=stock_price.price,
            status='open'
        )
        db.add(long_trade)

        # Create a short trade
        short_trade = Trade(
            symbol=stock_price.symbol,
            type='short',
            entry_price=stock_price.price,
            status='open'
        )
        db.add(short_trade)
        print(f"Opened long and short trades for {stock_price.symbol} at {stock_price.price}")

    db.commit()
    db.close()

@app.task
def evaluate_trades():
    db = SessionLocal()
    open_trades = db.query(Trade).filter(Trade.status == 'open').all()
    
    if not open_trades:
        print("No open trades to evaluate.")
        db.close()
        return

    # Get the most recent timestamp for each symbol
    latest_prices_subquery = db.query(
        StockPrice.symbol,
        func.max(StockPrice.timestamp).label('max_timestamp')
    ).group_by(StockPrice.symbol).subquery()

    latest_prices = db.query(StockPrice).join(
        latest_prices_subquery,
        (StockPrice.symbol == latest_prices_subquery.c.symbol) &
        (StockPrice.timestamp == latest_prices_subquery.c.max_timestamp)
    ).all()

    latest_prices_dict = {p.symbol: p.price for p in latest_prices}

    for trade in open_trades:
        current_price = latest_prices_dict.get(trade.symbol)

        if not current_price:
            print(f"Could not find current price for {trade.symbol}. Skipping trade {trade.id}.")
            continue

        pnl = 0.0
        if trade.type == 'long':
            pnl = (current_price - trade.entry_price) / trade.entry_price
        else: # short
            pnl = (trade.entry_price - current_price) / trade.entry_price

        # Check for stop-loss or take-profit
        if pnl >= 0.10:
            trade.status = 'closed'
            trade.result = 1
            trade.exit_price = current_price
            trade.closed_at = datetime.datetime.utcnow()
            print(f"Take-profit for trade {trade.id} ({trade.symbol} {trade.type}). PnL: {pnl:.2%}")
        elif pnl <= -0.10:
            trade.status = 'closed'
            trade.result = -1
            trade.exit_price = current_price
            trade.closed_at = datetime.datetime.utcnow()
            print(f"Stop-loss for trade {trade.id} ({trade.symbol} {trade.type}). PnL: {pnl:.2%}")

        # Check for time limit
        elif datetime.datetime.utcnow() - trade.created_at > datetime.timedelta(hours=1):
            trade.status = 'closed'
            trade.result = 0
            trade.exit_price = current_price
            trade.closed_at = datetime.datetime.utcnow()
            print(f"Trade {trade.id} ({trade.symbol} {trade.type}) closed due to time limit.")

    db.commit()
    db.close()

@app.task
def create_knn_trades():
    db = SessionLocal()
    latest_timestamp = db.query(KNNResult.created_at).order_by(desc(KNNResult.created_at)).first()
    if not latest_timestamp:
        print("No KNN results found to create trades.")
        db.close()
        return

    latest_timestamp = latest_timestamp[0]

    top_results = (
        db.query(KNNResult)
        .filter(KNNResult.created_at == latest_timestamp)
        .order_by(KNNResult.rank)
        .limit(20)
        .all()
    )

    if not top_results:
        print("No top KNN results found to create trades.")
        db.close()
        return

    symbols = {r.symbol for r in top_results}
    
    latest_prices_subquery = db.query(
        StockPrice.symbol,
        func.max(StockPrice.timestamp).label('max_timestamp')
    ).filter(StockPrice.symbol.in_(symbols)).group_by(StockPrice.symbol).subquery()

    latest_prices = db.query(StockPrice).join(
        latest_prices_subquery,
        (StockPrice.symbol == latest_prices_subquery.c.symbol) &
        (StockPrice.timestamp == latest_prices_subquery.c.max_timestamp)
    ).all()

    latest_prices_dict = {p.symbol: p.price for p in latest_prices}

    for result in top_results:
        current_price = latest_prices_dict.get(result.symbol)
        if not current_price:
            print(f"Could not find current price for {result.symbol}. Skipping trade creation.")
            continue

        trade = Trade(
            symbol=result.symbol,
            type=result.type,
            entry_price=current_price,
            status='open'
        )
        db.add(trade)
        print(f"Opened {result.type} trade for {result.symbol} at {current_price}")

    db.commit()
    db.close()

@app.task
def generate_dummy_knn_results():
    db = SessionLocal()
    symbols = ["AAPL", "GOOG", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "JNJ", "V", "PG", "WMT", "KO", "ORCL", "BAC"]
    
    # Clear existing dummy data
    db.query(KNNResult).delete()

    for i in range(10):
        long_result = KNNResult(
            symbol=random.choice(symbols),
            type='long',
            rank=i + 1,
        )
        db.add(long_result)

        short_result = KNNResult(
            symbol=random.choice(symbols),
            type='short',
            rank=i + 1,
        )
        db.add(short_result)
    
    db.commit()
    db.close()
