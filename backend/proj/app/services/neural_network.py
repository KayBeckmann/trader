"""
KNN-based Neural Network implementation using NumPy.
This module provides a simple feedforward neural network for stock prediction.
"""
import numpy as np
import os


class NeuralNetwork:
    """
    A feedforward neural network with configurable hidden layers.
    Uses sigmoid activation and backpropagation for training.
    """

    def __init__(self, input_size: int, hidden_layers: int = None, nodes_per_layer: int = None, output_size: int = 2):
        """
        Initialize the neural network.

        Args:
            input_size: Number of input features
            hidden_layers: Number of hidden layers (default from env or 2)
            nodes_per_layer: Nodes in each hidden layer (default from env or 16)
            output_size: Number of output nodes (2 for long/short prediction)
        """
        self.hidden_layers = hidden_layers or int(os.getenv('KNN_HIDDEN_LAYERS', 2))
        self.nodes_per_layer = nodes_per_layer or int(os.getenv('KNN_NODES_PER_LAYER', 16))
        self.input_size = input_size
        self.output_size = output_size

        self.weights = []
        self.biases = []

        self._initialize_weights()

    def _initialize_weights(self):
        """Initialize weights using Xavier initialization."""
        np.random.seed(42)

        # Input layer to first hidden layer
        prev_size = self.input_size

        for _ in range(self.hidden_layers):
            # Xavier initialization for better gradient flow
            limit = np.sqrt(6 / (prev_size + self.nodes_per_layer))
            w = np.random.uniform(-limit, limit, (prev_size, self.nodes_per_layer))
            b = np.zeros((1, self.nodes_per_layer))
            self.weights.append(w)
            self.biases.append(b)
            prev_size = self.nodes_per_layer

        # Last hidden layer to output layer
        limit = np.sqrt(6 / (prev_size + self.output_size))
        w = np.random.uniform(-limit, limit, (prev_size, self.output_size))
        b = np.zeros((1, self.output_size))
        self.weights.append(w)
        self.biases.append(b)

    @staticmethod
    def sigmoid(x: np.ndarray) -> np.ndarray:
        """Sigmoid activation function."""
        # Clip to avoid overflow
        x = np.clip(x, -500, 500)
        return 1 / (1 + np.exp(-x))

    @staticmethod
    def sigmoid_derivative(x: np.ndarray) -> np.ndarray:
        """Derivative of sigmoid function."""
        return x * (1 - x)

    @staticmethod
    def softmax(x: np.ndarray) -> np.ndarray:
        """Softmax activation for output layer."""
        exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)

    def forward(self, X: np.ndarray) -> tuple:
        """
        Forward propagation through the network.

        Args:
            X: Input data of shape (batch_size, input_size)

        Returns:
            Tuple of (output, activations) where activations is a list of all layer outputs
        """
        activations = [X]
        current = X

        # Hidden layers with sigmoid
        for i in range(len(self.weights) - 1):
            z = np.dot(current, self.weights[i]) + self.biases[i]
            current = self.sigmoid(z)
            activations.append(current)

        # Output layer with softmax
        z = np.dot(current, self.weights[-1]) + self.biases[-1]
        output = self.softmax(z)
        activations.append(output)

        return output, activations

    def backward(self, X: np.ndarray, y: np.ndarray, learning_rate: float = 0.01) -> float:
        """
        Backward propagation and weight update.

        Args:
            X: Input data
            y: Target labels (one-hot encoded)
            learning_rate: Learning rate for gradient descent

        Returns:
            Loss value
        """
        batch_size = X.shape[0]
        output, activations = self.forward(X)

        # Calculate cross-entropy loss
        epsilon = 1e-15
        loss = -np.mean(np.sum(y * np.log(output + epsilon), axis=1))

        # Output layer error (cross-entropy with softmax derivative)
        error = output - y

        # Backpropagate through layers
        deltas = [error]

        for i in range(len(self.weights) - 1, 0, -1):
            delta = np.dot(deltas[-1], self.weights[i].T) * self.sigmoid_derivative(activations[i])
            deltas.append(delta)

        deltas.reverse()

        # Update weights and biases
        for i in range(len(self.weights)):
            self.weights[i] -= learning_rate * np.dot(activations[i].T, deltas[i]) / batch_size
            self.biases[i] -= learning_rate * np.mean(deltas[i], axis=0, keepdims=True)

        return loss

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, learning_rate: float = 0.01, verbose: bool = False) -> list:
        """
        Train the neural network.

        Args:
            X: Training data
            y: Target labels (one-hot encoded)
            epochs: Number of training epochs
            learning_rate: Learning rate
            verbose: Print loss every 10 epochs

        Returns:
            List of loss values per epoch
        """
        losses = []

        for epoch in range(epochs):
            loss = self.backward(X, y, learning_rate)
            losses.append(loss)

            if verbose and epoch % 10 == 0:
                print(f"Epoch {epoch}, Loss: {loss:.4f}")

        return losses

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Input data

        Returns:
            Predicted class indices
        """
        output, _ = self.forward(X)
        return np.argmax(output, axis=1)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Get prediction probabilities.

        Args:
            X: Input data

        Returns:
            Probability distribution over classes
        """
        output, _ = self.forward(X)
        return output

    def save_weights(self, filepath: str):
        """Save model weights to file."""
        np.savez(filepath,
                 weights=np.array(self.weights, dtype=object),
                 biases=np.array(self.biases, dtype=object),
                 config=np.array([self.input_size, self.hidden_layers, self.nodes_per_layer, self.output_size]))

    def load_weights(self, filepath: str):
        """Load model weights from file."""
        data = np.load(filepath, allow_pickle=True)
        self.weights = list(data['weights'])
        self.biases = list(data['biases'])
        config = data['config']
        self.input_size = config[0]
        self.hidden_layers = config[1]
        self.nodes_per_layer = config[2]
        self.output_size = config[3]
