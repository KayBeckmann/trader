
import os
import time
import numpy as np
import database
from datetime import datetime, timedelta
import pytz

# Define market hours (as in data_fetcher)
MARKET_OPEN_HOUR_UTC = 14
MARKET_CLOSE_HOUR_UTC = 21
MARKET_DAYS_UTC = [0, 1, 2, 3, 4]

def is_market_open():
    """Checks if the stock market is currently open."""
    now_utc = datetime.now(pytz.utc)
    if now_utc.weekday() not in MARKET_DAYS_UTC:
        return False
    if MARKET_OPEN_HOUR_UTC <= now_utc.hour < MARKET_CLOSE_HOUR_UTC:
        return True
    return False

class NeuralNetwork:
    def __init__(self, input_size, hidden_layers, nodes_per_layer, output_size):
        self.input_size = input_size
        self.output_size = output_size
        self.hidden_layers = hidden_layers
        self.nodes_per_layer = nodes_per_layer

        self.weights = []
        self.biases = []

        # Initialization with random values
        layer_sizes = [input_size] + [nodes_per_layer] * hidden_layers + [output_size]
        for i in range(len(layer_sizes) - 1):
            # He initialization for weights
            self.weights.append(np.random.randn(layer_sizes[i], layer_sizes[i+1]) * np.sqrt(2. / layer_sizes[i]))
            self.biases.append(np.zeros((1, layer_sizes[i+1])))

    def _sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def _sigmoid_derivative(self, x):
        return x * (1 - x)

    def forward(self, X):
        self.activations = [X]
        self.z_values = []
        activation = X
        for i in range(len(self.weights)):
            z = np.dot(activation, self.weights[i]) + self.biases[i]
            self.z_values.append(z)
            activation = self._sigmoid(z)
            self.activations.append(activation)
        return activation

    def backward(self, X, y, output, learning_rate):
        error = y - output
        deltas = [error * self._sigmoid_derivative(output)]

        # Backpropagate the error
        for i in range(len(self.activations) - 2, 0, -1):
            error = deltas[-1].dot(self.weights[i].T)
            delta = error * self._sigmoid_derivative(self.activations[i])
            deltas.append(delta)
        
        deltas.reverse()

        # Update weights and biases
        for i in range(len(self.weights)):
            self.weights[i] += self.activations[i].T.dot(deltas[i]) * learning_rate
            self.biases[i] += np.sum(deltas[i], axis=0, keepdims=True) * learning_rate

    def train(self, X, y, epochs, learning_rate):
        for epoch in range(epochs):
            output = self.forward(X)
            self.backward(X, y, output, learning_rate)
            if epoch % 100 == 0:
                loss = np.mean(np.square(y - output))
                print(f"Epoch {epoch}, Loss: {loss:.4f}")

def get_training_data(db_conn):
    """Fetches training data from the last hour."""
    print("Fetching training data...")
    try:
        with db_conn.cursor() as cur:
            one_hour_ago = int(time.time()) - 3600
            cur.execute("""
                SELECT symbol, open_price, timestamp FROM training
                WHERE timestamp >= %s
                ORDER BY timestamp ASC
            """, (one_hour_ago,))
            data = cur.fetchall()
            print(f"Fetched {len(data)} records from the last hour.")
            return data
    except Exception as e:
        print(f"Error fetching training data: {e}")
        return []

def preprocess_data(data):
    """Normalizes data relative to the most recent data point."""
    if not data:
        return np.array([]), np.array([])

    # Group by symbol
    data_by_symbol = {}
    for symbol, price, ts in data:
        if symbol not in data_by_symbol:
            data_by_symbol[symbol] = []
        data_by_symbol[symbol].append(price)

    features = []
    labels = []

    for symbol, prices in data_by_symbol.items():
        if len(prices) < 2:
            continue # Need at least two data points
        
        prices = np.array(prices, dtype=float)
        latest_price = prices[-1]
        
        # Normalize relative to the latest price: (price - latest_price) / latest_price
        # This scales to a range around 0. We can clip to [-1, 1]
        normalized_prices = (prices[:-1] - latest_price) / latest_price
        normalized_prices = np.clip(normalized_prices, -1, 1)

        features.append(normalized_prices)
        # Example label: 1 if price increased, 0 otherwise (needs refinement)
        labels.append(1 if prices[-1] > prices[-2] else 0)

    return np.array(features), np.array(labels).reshape(-1, 1)

def main():
    """Main loop for the KNN worker."""
    print("Starting KNN worker service...")
    db_conn = database.get_db_connection()

    # Get NN configuration from environment variables
    try:
        hidden_layers = int(os.environ.get("KNN_HIDDEN_LAYERS", "2"))
        nodes_per_layer = int(os.environ.get("KNN_NODES_PER_LAYER", "16"))
    except ValueError:
        print("Invalid NN configuration in .env file. Using defaults.")
        hidden_layers = 2
        nodes_per_layer = 16

    # Wait for the market to open
    while not is_market_open():
        print("Market is closed. Waiting...")
        time.sleep(60)
    
    print("Market is open. Waiting 1 hour to start training...")
    time.sleep(3600)

    # Main training loop
    while True:
        if not is_market_open():
            print("Market closed. Stopping training for today.")
            # Wait until the next market open
            while not is_market_open():
                time.sleep(300)
            print("Market is open again. Waiting 1 hour...")
            time.sleep(3600)
            continue

        # 1. Fetch and preprocess data
        raw_data = get_training_data(db_conn)
        X, y = preprocess_data(raw_data)

        if X.size == 0 or y.size == 0:
            print("Not enough data to train. Waiting...")
            time.sleep(300) # Wait 5 minutes before retrying
            continue

        # 2. Initialize and train the model
        input_size = X.shape[1]
        output_size = 1 # Predict increase (1) or decrease (0)
        nn = NeuralNetwork(input_size, hidden_layers, nodes_per_layer, output_size)
        
        print("Starting model training...")
        nn.train(X, y, epochs=1000, learning_rate=0.01)
        print("Training finished.")

        # 3. Make predictions on the most recent data
        latest_features, _ = preprocess_data(raw_data[-12:]) # Use last 12 5-min intervals for prediction
        if latest_features.size > 0:
            prediction = nn.forward(latest_features)
            predicted_class = 1 if prediction[0][0] > 0.5 else 0
            
            # For simplicity, we predict for the first symbol in the batch
            predicted_symbol = raw_data[-1][0]
            prediction_type = 'long' if predicted_class == 1 else 'short'

            # Publish prediction to Redis
            try:
                redis_conn = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
                prediction_message = f"{{\"symbol\": \"{predicted_symbol}\", \"prediction\": \"{prediction_type}\"}}"
                redis_conn.publish('predictions', prediction_message)
                print(f"Published prediction: {prediction_message}")
            except Exception as e:
                print(f"Error publishing prediction to Redis: {e}")

        # 4. Wait before next training cycle
        print("Waiting for next training cycle...")
        time.sleep(300) # e.g., retrain every 5 minutes

if __name__ == "__main__":
    main()
