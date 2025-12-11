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

#### `backend`
<p>This Python service provides the FastAPI web server that acts as the interface between the frontend and the backend. It provides REST API endpoints for the frontend to fetch data (predictions, trade history, market hours, metrics) and a WebSocket endpoint for real-time prediction updates.</p>

#### `worker`
<p>This Celery worker handles background tasks including:</p>
<ul>
  <li><strong>Data Fetching:</strong> Periodically polls Yahoo Finance API for stock/crypto prices.</li>
  <li><strong>Training:</strong> Creates virtual long and short positions for each asset to generate training data. Positions are closed based on 10% stop-loss, 10% take-profit, or 1-hour timeout.</li>
  <li><strong>KNN Predictions:</strong> Uses a neural network (built from scratch with NumPy) to train on closed positions and generate top 10 long/short predictions.</li>
  <li><strong>Trading:</strong> Opens virtual trades based on predictions and manages them using stop-loss/take-profit logic.</li>
  <li><strong>Cleanup:</strong> Removes stocks with repeated data fetch failures from the tracking list.</li>
</ul>

#### `beat`
<p>This Celery beat scheduler triggers the worker tasks at configured intervals.</p>

#### `frontend`
<p>This container runs a Vue.js 3 development server (Vite). It serves the user interface of the application to the user's browser. It communicates with the <code>backend</code> via REST API and WebSocket for real-time updates.</p>

## Getting Started

To get the project running on your local machine, you will need Docker and Docker Compose installed.

1.  Clone the repository:
    ```sh
    git clone https://github.com/your-username/trader.git
    cd trader
    ```
2.  Create a local environment file from the example:
    ```sh
    cp env-example .env
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
The worker service will automatically pick up the changes.

**Note:** Stocks that fail to return data 3 times in a row will be automatically removed from tracking by the cleanup task.

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

-   `GET /api/knn/top`: Returns the latest top 10 long/short predictions.
-   `GET /api/trades`: Returns all closed trades from the database for P/L visualization.
-   `GET /api/market-hours`: Returns the stock market opening hours in UTC.
-   `GET /api/metrics`: Returns basic health and counters (DB/Redis status, counts for prices/training/trades, win rate, and latest predictions info).
-   `GET /api/health`: Simple health check endpoint.

### WebSocket

-   `ws://<host>/ws/predictions`: A WebSocket endpoint that pushes new predictions to connected clients in real-time. The messages are JSON strings with the format `{"long": [...], "short": [...]}`.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  PostgreSQL │
│   (Vue.js)  │◀────│  (FastAPI)  │◀────│             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           │ WebSocket
                           │
                    ┌──────┴──────┐
                    │    Redis    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌────┴────┐ ┌─────┴─────┐
        │  Worker   │ │  Beat   │ │  Worker   │
        │  (Celery) │ │(Celery) │ │  (Celery) │
        └───────────┘ └─────────┘ └───────────┘
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
