"""
KNN Service for stock prediction using the neural network.
Fetches training data from closed trades and generates predictions.
"""
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging
import redis
import json
import os

from .neural_network import NeuralNetwork
from ..models import Trade, StockPrice, KNNResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KNNService:
    """Service for training and making predictions with the neural network."""

    def __init__(self, db: Session):
        self.db = db
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)
        self.model = None
        self.feature_columns = ['price_change_1h', 'price_change_24h', 'volatility', 'volume_ratio']

    def _get_training_data(self, limit: int = 1000) -> tuple:
        """
        Get training data from closed trades.

        Returns:
            Tuple of (features, labels) as numpy arrays
        """
        # Get closed trades with results
        closed_trades = (
            self.db.query(Trade)
            .filter(Trade.status == 'closed', Trade.result.isnot(None))
            .order_by(desc(Trade.closed_at))
            .limit(limit)
            .all()
        )

        if len(closed_trades) < 10:
            logger.warning(f"Not enough training data: {len(closed_trades)} trades")
            return None, None

        features = []
        labels = []

        for trade in closed_trades:
            # Get price history for this symbol around the trade time
            trade_time = trade.created_at

            # Get prices for feature calculation
            prices = (
                self.db.query(StockPrice)
                .filter(
                    StockPrice.symbol == trade.symbol,
                    StockPrice.timestamp <= trade_time,
                    StockPrice.timestamp >= trade_time - timedelta(hours=24)
                )
                .order_by(desc(StockPrice.timestamp))
                .all()
            )

            if len(prices) < 2:
                continue

            # Calculate features
            current_price = prices[0].price
            prices_1h = [p.price for p in prices if p.timestamp >= trade_time - timedelta(hours=1)]
            prices_24h = [p.price for p in prices]

            if len(prices_1h) > 1 and len(prices_24h) > 1:
                price_change_1h = (current_price - prices_1h[-1]) / prices_1h[-1] if prices_1h[-1] != 0 else 0
                price_change_24h = (current_price - prices_24h[-1]) / prices_24h[-1] if prices_24h[-1] != 0 else 0
                volatility = np.std(prices_24h) / np.mean(prices_24h) if np.mean(prices_24h) != 0 else 0
                volume_ratio = len(prices_1h) / max(len(prices_24h) / 24, 1)

                feature_vector = [price_change_1h, price_change_24h, volatility, volume_ratio]
                features.append(feature_vector)

                # Label: 1 for profitable trade (result=1), 0 otherwise
                # For long trades: profit means price went up
                # For short trades: profit means price went down
                if trade.type == 'long':
                    label = 1 if trade.result == 1 else 0
                else:
                    label = 0 if trade.result == 1 else 1  # Inverse for short

                labels.append(label)

        if len(features) < 10:
            logger.warning(f"Not enough valid features: {len(features)}")
            return None, None

        X = np.array(features)
        y = np.eye(2)[labels]  # One-hot encode labels

        return X, y

    def _normalize_features(self, X: np.ndarray) -> np.ndarray:
        """Normalize features to [0, 1] range."""
        min_vals = X.min(axis=0)
        max_vals = X.max(axis=0)
        range_vals = max_vals - min_vals
        range_vals[range_vals == 0] = 1  # Avoid division by zero
        return (X - min_vals) / range_vals

    def train_model(self, epochs: int = 100, learning_rate: float = 0.01) -> bool:
        """
        Train the neural network model.

        Returns:
            True if training successful, False otherwise
        """
        X, y = self._get_training_data()

        if X is None or y is None:
            logger.error("Failed to get training data")
            return False

        logger.info(f"Training with {len(X)} samples")

        # Normalize features
        X = self._normalize_features(X)

        # Initialize and train model
        self.model = NeuralNetwork(input_size=len(self.feature_columns))
        losses = self.model.train(X, y, epochs=epochs, learning_rate=learning_rate, verbose=True)

        logger.info(f"Training complete. Final loss: {losses[-1]:.4f}")
        return True

    def get_current_features(self, symbol: str) -> np.ndarray:
        """Get current features for a symbol."""
        now = datetime.utcnow()

        prices = (
            self.db.query(StockPrice)
            .filter(
                StockPrice.symbol == symbol,
                StockPrice.timestamp >= now - timedelta(hours=24)
            )
            .order_by(desc(StockPrice.timestamp))
            .all()
        )

        if len(prices) < 2:
            return None

        current_price = prices[0].price
        prices_1h = [p.price for p in prices if p.timestamp >= now - timedelta(hours=1)]
        prices_24h = [p.price for p in prices]

        if len(prices_1h) < 1 or len(prices_24h) < 1:
            return None

        price_change_1h = (current_price - prices_1h[-1]) / prices_1h[-1] if prices_1h[-1] != 0 else 0
        price_change_24h = (current_price - prices_24h[-1]) / prices_24h[-1] if prices_24h[-1] != 0 else 0
        volatility = np.std(prices_24h) / np.mean(prices_24h) if np.mean(prices_24h) != 0 else 0
        volume_ratio = len(prices_1h) / max(len(prices_24h) / 24, 1)

        return np.array([[price_change_1h, price_change_24h, volatility, volume_ratio]])

    def generate_predictions(self) -> dict:
        """
        Generate top 10 long and short predictions.

        Returns:
            Dict with 'long' and 'short' lists of symbols with scores
        """
        # Get all unique symbols with recent prices (extended to 24 hours for reliability)
        recent_symbols = (
            self.db.query(StockPrice.symbol)
            .filter(StockPrice.timestamp >= datetime.utcnow() - timedelta(hours=24))
            .distinct()
            .all()
        )

        symbols = [s[0] for s in recent_symbols]

        if not symbols:
            logger.warning("No recent symbols found, using fallback predictions")
            return self._generate_fallback_predictions([])

        # If model not trained, train it first
        if self.model is None:
            if not self.train_model():
                logger.warning("Model training failed, using random predictions")
                return self._generate_fallback_predictions(symbols)

        predictions = []

        for symbol in symbols:
            features = self.get_current_features(symbol)
            if features is None:
                continue

            # Normalize features (simple min-max with assumed ranges)
            features = np.clip(features, -1, 1)

            proba = self.model.predict_proba(features)
            # proba[0][1] is probability of class 1 (bullish for long)
            long_score = proba[0][1]
            short_score = proba[0][0]

            predictions.append({
                'symbol': symbol,
                'long_score': float(long_score),
                'short_score': float(short_score)
            })

        # Sort by scores and get top 10
        top_long = sorted(predictions, key=lambda x: x['long_score'], reverse=True)[:10]
        top_short = sorted(predictions, key=lambda x: x['short_score'], reverse=True)[:10]

        return {
            'long': [{'symbol': p['symbol'], 'score': p['long_score']} for p in top_long],
            'short': [{'symbol': p['symbol'], 'score': p['short_score']} for p in top_short]
        }

    def _get_symbols_from_file(self) -> list:
        """Load symbols from stocks.txt file."""
        file_path = '/app/stocks.txt'
        if not os.path.exists(file_path):
            return []

        symbols = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        symbol = line.strip().split(',')[0]
                        symbols.append(symbol)
        except Exception as e:
            logger.error(f"Error reading stocks.txt: {e}")
        return symbols

    def _generate_fallback_predictions(self, symbols: list) -> dict:
        """Generate random predictions when model is not available."""
        import random

        # If no symbols provided, try to load from file
        if not symbols:
            symbols = self._get_symbols_from_file()
            logger.info(f"Loaded {len(symbols)} symbols from stocks.txt for fallback predictions")

        if not symbols:
            logger.warning("No symbols available for fallback predictions")
            return {'long': [], 'short': []}

        random.shuffle(symbols)
        top_symbols = symbols[:20]

        long_predictions = [{'symbol': s, 'score': 0.5 + random.random() * 0.3} for s in top_symbols[:10]]
        short_predictions = [{'symbol': s, 'score': 0.5 + random.random() * 0.3} for s in top_symbols[10:20]] if len(top_symbols) > 10 else []

        return {
            'long': long_predictions,
            'short': short_predictions
        }

    def save_predictions_to_db(self, predictions: dict):
        """Save predictions to database."""
        # Clear old predictions
        self.db.query(KNNResult).delete()

        for rank, pred in enumerate(predictions['long'], 1):
            result = KNNResult(
                symbol=pred['symbol'],
                type='long',
                rank=rank,
                score=pred.get('score')
            )
            self.db.add(result)

        for rank, pred in enumerate(predictions['short'], 1):
            result = KNNResult(
                symbol=pred['symbol'],
                type='short',
                rank=rank,
                score=pred.get('score')
            )
            self.db.add(result)

        self.db.commit()

    def publish_predictions(self, predictions: dict):
        """Publish predictions to Redis channel."""
        message = json.dumps(predictions)
        self.redis_client.publish('predictions', message)
        logger.info("Published predictions to Redis")
