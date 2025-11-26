from .celery import app
from .app.database import SessionLocal
from .app.models import StockPrice, SymbolFailure
import yfinance as yf
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_stock_symbols():
    # In docker, the CWD is /app
    file_path = '/app/stocks.txt'
    if not os.path.exists(file_path):
        return [] 

    symbols = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                symbol = line.strip().split(',')[0]
                symbols.append(symbol)
    return symbols

@app.task
def fetch_and_store_stock_data():
    db = SessionLocal()
    all_symbols = get_stock_symbols()
    if not all_symbols:
        logger.warning("No symbols found in stocks.txt")
        db.close()
        return "No symbols found in stocks.txt"

    # Get currently blocked symbols
    blocked_symbols = db.query(SymbolFailure).filter(SymbolFailure.failure_count >= 3).all()
    blocked_symbol_set = {s.symbol for s in blocked_symbols}
    
    symbols_to_fetch = [s for s in all_symbols if s not in blocked_symbol_set]

    logger.info(f"Fetching data for {len(symbols_to_fetch)} of {len(all_symbols)} total symbols...")
    for symbol in symbols_to_fetch:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty and not hist['Close'].empty:
                price = hist['Close'].iloc[-1]
                stock_price = StockPrice(symbol=symbol, price=price)
                db.add(stock_price)
                logger.info(f"Fetched {symbol}: {price}")

                # On success, reset failure count if it exists
                failure_record = db.query(SymbolFailure).filter(SymbolFailure.symbol == symbol).first()
                if failure_record:
                    failure_record.failure_count = 0
            else:
                raise ValueError(f"No history data found for {symbol}")

        except Exception as e:
            logger.error(f"Could not fetch data for {symbol}: {e}")
            
            # On failure, increment failure count
            failure_record = db.query(SymbolFailure).filter(SymbolFailure.symbol == symbol).first()
            if failure_record:
                failure_record.failure_count += 1
            else:
                # Create new failure record
                failure_record = SymbolFailure(symbol=symbol, failure_count=1)
                db.add(failure_record)
            
            logger.warning(f"Failure count for {symbol} is now {failure_record.failure_count}")

    db.commit()
    logger.info("Finished fetching stock data and committed to database.")
    db.close()
    return f"Attempted to store prices for {len(symbols_to_fetch)} symbols."
