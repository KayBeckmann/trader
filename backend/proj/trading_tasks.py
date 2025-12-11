from .celery import app
from .app.database import SessionLocal
from .app.models import StockPrice, Trade, KNNResult, SymbolFailure
from sqlalchemy import func, desc
import datetime
import logging
import redis
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.task
def open_trades():
    """Open virtual long and short trades for all stocks at current prices."""
    db = SessionLocal()

    # Get the most recent timestamp from stock_prices
    latest_timestamp = db.query(func.max(StockPrice.timestamp)).scalar()

    if not latest_timestamp:
        logger.warning("No stock prices found to open trades.")
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
        logger.info(f"Opened long and short trades for {stock_price.symbol} at {stock_price.price}")

    db.commit()
    db.close()


@app.task
def evaluate_trades():
    """Evaluate open trades and close them based on stop-loss, take-profit, or timeout."""
    db = SessionLocal()
    open_trades = db.query(Trade).filter(Trade.status == 'open').all()

    if not open_trades:
        logger.debug("No open trades to evaluate.")
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
            logger.debug(f"Could not find current price for {trade.symbol}. Skipping trade {trade.id}.")
            continue

        pnl = 0.0
        if trade.type == 'long':
            pnl = (current_price - trade.entry_price) / trade.entry_price
        else:  # short
            pnl = (trade.entry_price - current_price) / trade.entry_price

        # Check for stop-loss or take-profit
        if pnl >= 0.10:
            trade.status = 'closed'
            trade.result = 1
            trade.exit_price = current_price
            trade.closed_at = datetime.datetime.utcnow()
            logger.info(f"Take-profit for trade {trade.id} ({trade.symbol} {trade.type}). PnL: {pnl:.2%}")
        elif pnl <= -0.10:
            trade.status = 'closed'
            trade.result = -1
            trade.exit_price = current_price
            trade.closed_at = datetime.datetime.utcnow()
            logger.info(f"Stop-loss for trade {trade.id} ({trade.symbol} {trade.type}). PnL: {pnl:.2%}")

        # Check for time limit (1 hour)
        elif datetime.datetime.utcnow() - trade.created_at > datetime.timedelta(hours=1):
            trade.status = 'closed'
            trade.result = 0
            trade.exit_price = current_price
            trade.closed_at = datetime.datetime.utcnow()
            logger.info(f"Trade {trade.id} ({trade.symbol} {trade.type}) closed due to time limit.")

    db.commit()
    db.close()


@app.task
def create_knn_trades():
    """Create trades based on KNN predictions."""
    db = SessionLocal()
    latest_timestamp = db.query(KNNResult.created_at).order_by(desc(KNNResult.created_at)).first()
    if not latest_timestamp:
        logger.debug("No KNN results found to create trades.")
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
        logger.debug("No top KNN results found to create trades.")
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
            logger.debug(f"Could not find current price for {result.symbol}. Skipping trade creation.")
            continue

        trade = Trade(
            symbol=result.symbol,
            type=result.type,
            entry_price=current_price,
            status='open'
        )
        db.add(trade)
        logger.info(f"Opened {result.type} trade for {result.symbol} at {current_price}")

    db.commit()
    db.close()


@app.task
def generate_knn_predictions():
    """Generate KNN predictions using the neural network."""
    from .app.services.knn_service import KNNService

    db = SessionLocal()
    try:
        knn_service = KNNService(db)

        # Train model and generate predictions
        logger.info("Generating KNN predictions...")
        predictions = knn_service.generate_predictions()

        if predictions['long'] or predictions['short']:
            # Save to database
            knn_service.save_predictions_to_db(predictions)

            # Publish to Redis for WebSocket
            knn_service.publish_predictions(predictions)

            logger.info(f"Generated {len(predictions['long'])} long and {len(predictions['short'])} short predictions")
        else:
            logger.warning("No predictions generated")

    except Exception as e:
        logger.error(f"Error generating KNN predictions: {e}")
    finally:
        db.close()


@app.task
def remove_failed_stocks():
    """Remove stocks that have failed to fetch data 3+ times from stocks.txt."""
    db = SessionLocal()
    try:
        # Get symbols with 3 or more failures
        failed_symbols = db.query(SymbolFailure).filter(SymbolFailure.failure_count >= 3).all()

        if not failed_symbols:
            logger.info("No failed symbols to remove")
            return

        failed_symbol_set = {s.symbol for s in failed_symbols}
        logger.info(f"Found {len(failed_symbol_set)} symbols to remove: {failed_symbol_set}")

        # Read current stocks.txt
        file_path = '/app/stocks.txt'
        if not os.path.exists(file_path):
            logger.warning("stocks.txt not found")
            return

        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Filter out failed symbols
        new_lines = []
        removed = []
        for line in lines:
            if line.strip():
                symbol = line.strip().split(',')[0]
                if symbol not in failed_symbol_set:
                    new_lines.append(line)
                else:
                    removed.append(symbol)

        # Write updated file
        with open(file_path, 'w') as f:
            f.writelines(new_lines)

        # Clear the failure records for removed symbols
        for symbol in removed:
            db.query(SymbolFailure).filter(SymbolFailure.symbol == symbol).delete()

        db.commit()
        logger.info(f"Removed {len(removed)} failed symbols from stocks.txt: {removed}")

    except Exception as e:
        logger.error(f"Error removing failed stocks: {e}")
    finally:
        db.close()


# Keep the dummy function for backwards compatibility during transition
@app.task
def generate_dummy_knn_results():
    """
    DEPRECATED: Use generate_knn_predictions instead.
    This function now calls the real KNN prediction generator.
    """
    generate_knn_predictions.delay()
