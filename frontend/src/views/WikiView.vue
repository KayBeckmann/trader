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
