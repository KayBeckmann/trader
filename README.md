# Stock Trader AI

**Forschungsprojekt und KEINE Anlageberatung**

This project is a web-based application that uses a neural network to analyze stock data and predict the top 10 "long" and top 10 "short" stocks.

## Architecture

The application is built with a microservices architecture and runs entirely in Docker containers, managed by Docker Compose.

- **Frontend:** A responsive web interface built with **Vue.js 3**. It communicates with the backend via a REST API and receives real-time updates through WebSockets.

- **Backend:** The backend is split into multiple Python services that communicate via **Redis**:
  - **1. Data-Fetcher:** Periodically polls a financial data source (Yahoo Finance) every 5 minutes to retrieve the latest stock and crypto information and saves it to the database.
  - **2. Trainer:** Creates virtual long and short positions for training purposes. It automatically closes these positions based on a 10% stop-loss, 10% take-profit, or a 1-hour timeout.
  - **3. KNN-Worker:** The core of the application. This service uses a neural network (built from scratch with NumPy) that is trained using reinforcement learning on the results of the closed training positions. It then predicts the top 10 long and short assets and publishes them.
  - **4. Trader:** Consumes the predictions from the KNN-Worker and opens virtual trades. It manages these trades with the same stop-loss/take-profit/timeout logic as the trainer.
  - **5. API-Server:** A FastAPI server that provides REST endpoints for the frontend and handles WebSocket connections for real-time updates.

- **Database:** A **PostgreSQL** database is used for storing historical price data, training positions, and live trades.

- **Communication:** A **Redis** instance is used as a message broker for communication between the backend services.

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