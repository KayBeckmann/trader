import os
import time
import json
import numpy as np
import redis
import database

def get_redis_connection():
    """Establishes a connection to Redis."""
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

class NeuralNetwork:
    def __init__(self, input_size, hidden_layers, nodes_per_layer, output_size):
        self.input_size = input_size
        self.output_size = output_size
        self.hidden_layers = hidden_layers
        self.nodes_per_layer = nodes_per_layer

        self.weights = []
        self.biases = []

        layer_sizes = [input_size] + [nodes_per_layer] * hidden_layers + [output_size]
        for i in range(len(layer_sizes) - 1):
            self.weights.append(np.random.randn(layer_sizes[i], layer_sizes[i+1]) * np.sqrt(2. / layer_sizes[i]))
            self.biases.append(np.zeros((1, layer_sizes[i+1])))

    def _relu(self, x):
        return np.maximum(0, x)

    def _relu_derivative(self, x):
        return np.where(x > 0, 1, 0)

    def _softmax(self, x):
        exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)

    def forward(self, X):
        self.activations = [X]
        activation = X
        for i in range(len(self.weights) - 1):
            z = np.dot(activation, self.weights[i]) + self.biases[i]
            activation = self._relu(z)
            self.activations.append(activation)
        
        # Output layer with softmax
        z_out = np.dot(activation, self.weights[-1]) + self.biases[-1]
        output = self._softmax(z_out)
        self.activations.append(output)
        return output

    def backward(self, X, y, output, learning_rate):
        # y is one-hot encoded
        error = output - y
        deltas = [error]

        for i in range(len(self.weights) - 1, 0, -1):
            error = deltas[-1].dot(self.weights[i].T)
            delta = error * self._relu_derivative(self.activations[i])
            deltas.append(delta)
        
        deltas.reverse()

        for i in range(len(self.weights)):
            self.weights[i] -= self.activations[i].T.dot(deltas[i]) * learning_rate
            self.biases[i] -= np.sum(deltas[i], axis=0, keepdims=True) * learning_rate

    def train(self, X, y, epochs, learning_rate):
        for epoch in range(epochs):
            output = self.forward(X)
            self.backward(X, y, output, learning_rate)
            if epoch % 100 == 0:
                loss = -np.mean(y * np.log(output + 1e-8))
                print(f"Epoch {epoch}, Loss: {loss:.4f}")

def get_training_data(db_conn):
    """Fetches closed training trades from the database."""
    print("Fetching closed training data...")
    try:
        with db_conn.cursor() as cur:
            cur.execute("SELECT symbol, open_price, profit_loss, timestamp, order_size FROM training WHERE status = 'closed'")
            data = cur.fetchall()
            # Mark as processed to avoid re-training
            cur.execute("UPDATE training SET status = 'processed' WHERE status = 'closed'")
            db_conn.commit()
            print(f"Fetched {len(data)} closed trades.")
            return data
    except Exception as e:
        print(f"Error fetching training data: {e}")
        return []

def preprocess_data(db_conn, closed_trades):
    """Generates features and labels from closed trades."""
    features = []
    labels = []

    for trade in closed_trades:
        symbol, open_price, profit_loss, open_ts, order_size = trade
        
        # 1. Get historical data for features
        try:
            with db_conn.cursor() as cur:
                # Fetch last 12 5-min prices before the trade opened
                cur.execute("""
                    SELECT price FROM stock_prices 
                    WHERE symbol = %s AND timestamp < %s
                    ORDER BY timestamp DESC LIMIT 12
                """, (symbol, open_ts))
                prices = cur.fetchall()
                if len(prices) < 12:
                    continue # Not enough historical data

                prices = np.array([p[0] for p in prices], dtype=float)
                # Normalize relative to the opening price
                normalized_prices = (prices - open_price) / open_price
                features.append(normalized_prices.flatten())

                # 2. Determine label based on profit/loss percentage
                pnl_percentage = (profit_loss / order_size) * 100
                if pnl_percentage > 2:
                    labels.append([1, 0, 0])  # Positive
                elif pnl_percentage < -2:
                    labels.append([0, 0, 1])  # Negative
                else:
                    labels.append([0, 1, 0])  # Neutral

        except Exception as e:
            print(f"Error preprocessing data for {symbol}: {e}")

    return np.array(features), np.array(labels)

def predict_top_assets(db_conn, model):
    """Predicts the top 10 long and short assets."""
    print("Predicting top assets...")
    predictions = {}
    try:
        with db_conn.cursor() as cur:
            # Get all unique symbols
            cur.execute("SELECT DISTINCT symbol FROM stock_prices")
            symbols = [row[0] for row in cur.fetchall()]

            for symbol in symbols:
                # Get latest 12 data points for prediction
                cur.execute("SELECT price FROM stock_prices WHERE symbol = %s ORDER BY timestamp DESC LIMIT 12", (symbol,))
                prices = cur.fetchall()
                if len(prices) < 12:
                    continue

                prices = np.array([p[0] for p in prices], dtype=float)
                # Normalize with the most recent price
                normalized_prices = (prices - prices[0]) / prices[0]
                
                prediction = model.forward(normalized_prices.reshape(1, -1))
                predictions[symbol] = prediction[0]

        # Sort by confidence
        long_candidates = sorted(predictions.items(), key=lambda item: item[1][0], reverse=True)
        short_candidates = sorted(predictions.items(), key=lambda item: item[1][2], reverse=True)

        top_10_long = [item[0] for item in long_candidates[:10]]
        top_10_short = [item[0] for item in short_candidates[:10]]

        return top_10_long, top_10_short

    except Exception as e:
        print(f"Error during prediction: {e}")
        return [], []

def main():
    """Main loop for the KNN worker."""
    print("Starting KNN worker service...")
    database.initialize_database()
    db_conn = database.get_db_connection()
    redis_conn = get_redis_connection()

    hidden_layers = int(os.environ.get("KNN_HIDDEN_LAYERS", "2"))
    nodes_per_layer = int(os.environ.get("KNN_NODES_PER_LAYER", "16"))
    input_size = 12 # 12 data points
    output_size = 3   # [Positive, Neutral, Negative]

    nn = NeuralNetwork(input_size, hidden_layers, nodes_per_layer, output_size)

    while True:
        print("Checking for new training data...")
        closed_trades = get_training_data(db_conn)

        if closed_trades:
            X, y = preprocess_data(db_conn, closed_trades)
            if X.size > 0 and y.size > 0:
                print(f"Training model with {len(X)} new samples...")
                nn.train(X, y, epochs=1000, learning_rate=0.01)
                print("Training finished.")

                # After training, make new predictions
                top_long, top_short = predict_top_assets(db_conn, nn)
                if top_long or top_short:
                    prediction_message = json.dumps({'long': top_long, 'short': top_short})
                    try:
                        redis_conn.publish('predictions', prediction_message)
                        print(f"Published predictions: {prediction_message}")
                    except Exception as e:
                        print(f"Error publishing predictions: {e}")

        print("Waiting for 5 minutes before next cycle...")
        time.sleep(300)

if __name__ == "__main__":
    main()