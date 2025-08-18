<template>
  <div class="wiki">
    <h1>Project Wiki</h1>

    <section>
      <h2>Stock Trader AI</h2>
      <p><strong>Forschungsprojekt und KEINE Anlageberatung</strong></p>
      <p>This project is a web-based application that uses a neural network to analyze stock data and predict the top 10 "long" and top 10 "short" stocks.</p>
    </section>

    <section>
      <h2>Architecture</h2>
      <p>The application is built with a microservices architecture and runs entirely in Docker containers, managed by Docker Compose.</p>
      <ul>
        <li><strong>Frontend:</strong> A responsive web interface built with <strong>Vue.js 3</strong>. It is intended to communicate with the backend via a REST API and receive real-time updates through WebSockets.</li>
        <li><strong>Backend:</strong> The backend is split into four distinct Python services that communicate via <strong>Redis</strong>:
          <ul>
            <li><strong>1. Data-Fetcher:</strong> This service periodically polls a financial data source every 5 minutes to retrieve the latest stock and crypto information and saves it to the database.</li>
            <li><strong>2. Trainer:</strong> This service creates virtual long and short positions for training purposes. It automatically closes these positions based on a 10% stop-loss, 10% take-profit, or a 1-hour timeout.</li>
            <li><strong>3. KNN-Worker:</strong> The core of the application. This service uses a neural network (built from scratch with NumPy) that is trained using reinforcement learning on the results of the closed training positions. It then predicts the top 10 long and short assets and publishes them.</li>
            <li><strong>4. Trader:</strong> This service consumes the predictions from the KNN-Worker and opens virtual trades. It manages these trades with the same stop-loss/take-profit/timeout logic as the trainer.</li>
          </ul>
        </li>
        <li><strong>Database:</strong> A <strong>PostgreSQL</strong> database is used for storing historical price data, training positions, and live trades.</li>
        <li><strong>Communication:</strong> A <strong>Redis</strong> instance is used as a message broker for communication between the backend services.</li>
      </ul>
    </section>

    <section>
      <h2>Docker Container Details</h2>
      <p>The application is composed of several Docker containers that work together. Here is a detailed description of each container:</p>
      
      <h4><code>postgres</code></h4>
      <p>This container runs a PostgreSQL 13 database server. It is used to store all persistent data, including:</p>
      <ul>
        <li>Historical stock and crypto prices.</li>
        <li>Training data for the neural network (virtual long/short positions).</li>
        <li>Live (virtual) trades and their profit/loss results.</li>
      </ul>
      <p>The data is stored in the <code>/data/postgres_data</code> directory on the host machine, which is mounted as a volume to ensure data persistence even if the container is removed.</p>

      <h4><code>redis</code></h4>
      <p>This container runs a Redis 7 instance. Redis is an in-memory data store used as a message broker for asynchronous communication between the backend services. It ensures that the services are decoupled and can communicate efficiently.</p>

      <h4><code>data-fetcher</code></h4>
      <p>This Python service is responsible for fetching financial data. It periodically (every 5 minutes) polls the Yahoo Finance API for the latest prices of stocks and cryptocurrencies listed in <code>stocks.txt</code>. The fetched data is then saved to the PostgreSQL database. It also publishes a message to the 'data-fetched' channel in Redis to notify other services that new data is available.</p>

      <h4><code>trainer</code></h4>
      <p>This Python service listens for messages on the 'data-fetched' Redis channel. When new data arrives, it creates virtual long and short positions for each asset to generate training data for the neural network. These positions are closed based on a set of rules: 10% stop-loss, 10% take-profit, or a 1-hour timeout. The results of these closed positions are stored in the database.</p>

      <h4><code>knn-worker</code></h4>
      <p>This is the core of the AI functionality. This Python service uses a K-Nearest Neighbors (KNN) based neural network (built from scratch with NumPy) to perform reinforcement learning. It fetches the results of the closed training positions from the database to train the model. After training, it uses the model to predict the top 10 "long" and top 10 "short" assets. These predictions are then published to the 'predictions' channel on Redis.</p>

      <h4><code>trader</code></h4>
      <p>This Python service subscribes to the 'predictions' Redis channel. When it receives a new list of predictions from the <code>knn-worker</code>, it opens new virtual trades in the database. It manages these trades using the same stop-loss, take-profit, and timeout logic as the <code>trainer</code> service. The results of these trades are used for the profit/loss visualization on the frontend.</p>

      <h4><code>api-server</code></h4>
      <p>This Python service is a FastAPI web server that acts as the interface between the frontend and the backend. It provides several REST API endpoints for the frontend to fetch initial data (e.g., predictions, trade history, market hours). It also provides a WebSocket endpoint that allows the frontend to receive real-time updates for the predictions as soon as they are published by the <code>knn-worker</code>.</p>

      <h4><code>frontend</code></h4>
      <p>This container runs a Vue.js 3 development server (Vite). It serves the user interface of the application to the user's browser. It communicates with the <code>api-server</code> to display data and receive real-time updates.</p>
    </section>

    <section>
      <h2>Frontend User Guide</h2>
      <p>The frontend provides a simple interface to view the AI's predictions and the performance of the virtual trades.</p>

      <h4>Market Status</h4>
      <p>At the top of the page, you can see the current status of the stock market (OPEN or CLOSED). The market hours are displayed in your local timezone.</p>

      <h4>Predictions</h4>
      <p>The main part of the page is divided into two lists: "Top 10 Long" and "Top 10 Short". These lists are updated in real-time as the AI model generates new predictions. "Long" predictions are stocks that the AI expects to rise in price, while "short" predictions are stocks that are expected to fall.</p>

      <h4>Profit/Loss History</h4>
      <p>Below the prediction lists, you will find a chart that visualizes the cumulative profit and loss (P/L) of all closed virtual trades over time. This chart gives you an idea of the historical performance of the trading strategy.</p>
      
      <h4>How to Add/Change Stocks</h4>
      <p>The application is configured to track a list of stocks defined in the <code>stocks.txt</code> file at the root of the project. To change the stocks that the AI analyzes, you can edit this file. Each line should contain a stock symbol (as used by Yahoo Finance) followed by a comma and the asset type (`stock` or `crypto`). For example:</p>
      <code>
        AAPL,stock<br>
        GOOG,stock<br>
        BTC-USD,crypto
      </code>
      <p>After saving the file, the <code>data-fetcher</code> service will automatically start tracking the new symbols on its next cycle.</p>
    </section>
    
    <section>
        <h2>Microservices Communication</h2>
        <p>The backend is split into logical, independent services, each running in its own Docker container. Communication between these containers is asynchronous using a message broker (Redis).</p>
        <p>The process looks like this:</p>
        <ol>
            <li>The frontend sends a request to the API service.</li>
            <li>The API service creates a "job" (a message) and puts it in a queue in the message broker (e.g., fetch-queue). It then immediately sends a response to the frontend ("Request accepted").</li>
            <li>The Fetcher service listens to the fetch-queue. As soon as a message is there, it takes it, fetches the data, and after its work is done, it puts a new message in the process-queue.</li>
            <li>The Processor service listens to the process-queue, takes the message, processes the data, and saves the result in the database.</li>
        </ol>
    </section>

    <section>
      <h2>Getting Started</h2>
      <p>To get the project running on your local machine, you will need Docker and Docker Compose installed.</p>
      <ol>
        <li>Clone the repository.</li>
        <li>Create a local environment file from the example: <code>cp env-exmample .env</code></li>
        <li>Update the <code>.env</code> file with your specific configurations if needed.</li>
        <li>Build and run the application using Docker Compose: <code>docker-compose up --build</code></li>
      </ol>
      <p>Once the containers are running, the frontend will be accessible at <code>http://localhost:5173</code>.</p>
    </section>
  </div>
</template>

<script>
export default {
  name: 'WikiView'
}
</script>

<style scoped>
.wiki {
  text-align: left;
}
section {
  margin-bottom: 2rem;
}
h1, h2 {
  border-bottom: 1px solid #ccc;
  padding-bottom: 0.5rem;
  margin-bottom: 1rem;
}
code {
  background-color: #eee;
  padding: 2px 4px;
  border-radius: 4px;
}
</style>
