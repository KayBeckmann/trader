# Stock Trader AI

**Forschungsprojekt und KEINE Anlageberatung**

This project is a web-based application that uses a neural network to analyze stock data and predict the top 10 "long" and top 10 "short" stocks.

## Services

The application is composed of several Docker containers that work together. Here is a detailed description of each container:

#### `postgres`
<p>This container runs a PostgreSQL 13 database server. It is used to store all persistent data, including:</p>
<ul>
  <li>Historical stock and crypto prices.</li>
  <li>Training data for the neural network (virtual long/short positions).</li>
  <li>Live (virtual) trades and their profit/loss results.</li>
</ul>
<p>The data is stored in the <code>/data/postgres_data</code> directory on the host machine, which is mounted as a volume to ensure data persistence even if the container is removed.</p>

#### `redis`
<p>This container runs a Redis 7 instance. Redis is an in-memory data store used as a message broker for asynchronous communication between the backend services. It ensures that the services are decoupled and can communicate efficiently.</p>

#### `data-fetcher`
<p>This Python service is responsible for fetching financial data. It periodically (every 5 minutes) polls the Yahoo Finance API for the latest prices of stocks and cryptocurrencies listed in <code>stocks.txt</code>. The fetched data is then saved to the PostgreSQL database. It also publishes a message to the 'data-fetched' channel in Redis to notify other services that new data is available.</p>

#### `trainer`
<p>This Python service listens for messages on the 'data-fetched' Redis channel. When new data arrives, it creates virtual long and short positions for each asset to generate training data for the neural network. These positions are closed based on a set of rules: 10% stop-loss, 10% take-profit, or a 1-hour timeout. The results of these closed positions are stored in the database.</p>

#### `knn-worker`
<p>This is the core of the AI functionality. This Python service uses a K-Nearest Neighbors (KNN) based neural network (built from scratch with NumPy) to perform reinforcement learning. It fetches the results of the closed training positions from the database to train the model. After training, it uses the model to predict the top 10 "long" and top 10 "short" assets. These predictions are then published to the 'predictions' channel on Redis.</p>

#### `trader`
<p>This Python service subscribes to the 'predictions' Redis channel. When it receives a new list of predictions from the <code>knn-worker</code>, it opens new virtual trades in the database. It manages these trades using the same stop-loss, take-profit, and timeout logic as the <code>trainer</code> service. The results of these trades are used for the profit/loss visualization on the frontend.</p>

#### `api-server`
<p>This Python service is a FastAPI web server that acts as the interface between the frontend and the backend. It provides several REST API endpoints for the frontend to fetch initial data (e.g., predictions, trade history, market hours). It also provides a WebSocket endpoint that allows the frontend to receive real-time updates for the predictions as soon as they are published by the <code>knn-worker</code>.</p>

#### `frontend`
<p>This container runs a Vue.js 3 development server (Vite). It serves the user interface of the application to the user's browser. It communicates with the <code>api-server</code> to display data and receive real-time updates.</p>

## Getting Started

To get the project running on your local machine, you will need Docker and Docker Compose installed.

1.  Clone the repository:
    ```sh
    git clone https://github.com/your-username/trader.git
    cd trader
    ```
2.  Create a local environment file from the example:
    ```sh
    cp env-exmample .env
    ```
3.  Update the `.env` file with your specific configurations if needed (see Configuration section below).

4.  Build and run the application using Docker Compose:
    ```sh
    docker-compose up --build
    ```

Once the containers are running, the frontend will be accessible at `http://localhost:5173` (or the port you configure in `.env`).

## Usage

To add or change the stocks that are being tracked, edit the `stocks.txt` file. Each line should contain a stock symbol followed by a comma and the asset type (`stock` or `crypto`). For example:
```
AAPL,stock
BTC-USD,crypto
```
The `data-fetcher` service will automatically pick up the changes.

## Configuration

The `.env` file is used for configuration. The following variables are available:

| Variable              | Description                                                                                             | Default Value   |
| --------------------- | ------------------------------------------------------------------------------------------------------- | --------------- |
| `POSTGRES_USER`       | Username for the PostgreSQL database.                                                                   | `trader_user`   |
| `POSTGRES_PASSWORD`   | Password for the PostgreSQL database.                                                                   | `trader_password`|
| `POSTGRES_DB`         | Name of the PostgreSQL database.                                                                        | `trader_db`     |
| `POSTGRES_PORT`       | The external port to map to the PostgreSQL container's port 5432.                                       | `5432`          |
| `BACKEND_PORT`        | The external port to map to the backend API server's port 8000.                                         | `8000`          |
| `FRONTEND_PORT`       | The external port to map to the frontend development server's port 5173.                                | `5173`          |
| `VITE_ALLOWED_HOST`   | The hostname that the Vite development server will accept. Set this if you access the frontend from a different host than `localhost`. | `projekt.beckmann-md.de` |
| `KNN_HIDDEN_LAYERS`   | The number of hidden layers in the neural network.                                                      | `2`             |
| `KNN_NODES_PER_LAYER` | The number of nodes in each hidden layer of the neural network.                                         | `16`            |


## API Endpoints

The backend provides the following API endpoints:

### REST API

-   `GET /api/market-hours`: Returns the stock market opening hours in UTC.
-   `GET /api/predictions`: Returns the latest top 10 long/short predictions from Redis.
-   `GET /api/trades`: Returns all closed trades from the database for P/L visualization.

### WebSocket

-   `ws:///ws/predictions`: A WebSocket endpoint that pushes new predictions to connected clients in real-time. The messages are JSON strings with the format `{"long": [...], "short": [...]}`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.