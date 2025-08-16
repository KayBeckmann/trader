# Stock Trader AI

**Forschungsprojekt und KEINE Anlageberatung**

This project is a web-based application that uses a neural network to analyze stock data and predict the top 10 "long" and top 10 "short" stocks.

## Architecture

The application is built with a microservices architecture and runs entirely in Docker containers, managed by Docker Compose.

- **Frontend:** A responsive web interface built with **Vue.js 3**. It is intended to communicate with the backend via a REST API and receive real-time updates through WebSockets (API-Server not yet implemented).

- **Backend:** The backend is split into four distinct Python services that communicate via **Redis**:
  - **1. Data-Fetcher:** This service periodically polls a financial data source every 5 minutes to retrieve the latest stock and crypto information and saves it to the database.
  - **2. Trainer:** This service creates virtual long and short positions for training purposes. It automatically closes these positions based on a 10% stop-loss, 10% take-profit, or a 1-hour timeout.
  - **3. KNN-Worker:** The core of the application. This service uses a neural network (built from scratch with NumPy) that is trained using reinforcement learning on the results of the closed training positions. It then predicts the top 10 long and short assets and publishes them.
  - **4. Trader:** This service consumes the predictions from the KNN-Worker and opens virtual trades. It manages these trades with the same stop-loss/take-profit/timeout logic as the trainer.

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
3.  Update the `.env` file with your specific configurations if needed (e.g., database credentials, ports).

4.  Build and run the application using Docker Compose:
    ```sh
    docker-compose up --build
    ```

Once the containers are running, the frontend will be accessible at `http://localhost:5173` (or the port you configure in `.env`).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.