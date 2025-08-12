# Gemini Notes

This file contains notes and context for the Gemini assistant.

## Project: Stock Trader AI

- **Goal:** Build an application to predict stock movements using a neural network.
- **Data Source:** MSCI World All Countries index.
- **Core Logic:**
    - Fetch current and historical stock data.
    - Use a neural network to predict top 10 long and top 10 short stocks.
    - Run only during stock market opening hours.
    - Evaluate performance after 1 and 2 hours and retrain via backpropagation.
- **Tech Stack:**
    - **Backend:** Python, FastAPI. The backend will be split into three services:
        - **Data-Fetcher:** A container that polls data from the source every 5 minutes.
        - **KNN-Worker:** A container that runs the neural network calculations.
        - **API-Server:** A container that provides a REST and WebSocket API for the frontend.
    - **Real-time Communication:** WebSockets will be used to push updates from the API-Server to the frontend automatically.
    - **Database:** PostgreSQL (confirmed from start)
    - **Neural Network:** STRICTLY from scratch using NumPy. NO TensorFlow, PyTorch, or other frameworks. Activation: tanh. Random weight initialization.
    - **Frontend:** Vue.js 3 (responsive)
- **Deployment:**
    - Docker-first approach.
    - Separate containers for each service (Data-Fetcher, KNN-Worker, API-Server, Frontend, DB).
    - Managed via Docker Compose.
- **Web UI Features:**
    - Display top 10 long/short lists (updated in real-time).
    - Display P/L graph.
    - Display market opening hours, converted to user's timezone.
    - **Internal Wiki:** A section in the frontend for documenting the application's functionality and architecture.

## Workflow
- After each successfully completed step, I will mark the task as done in `todo.md`.
- I will create a new Git commit after every significant, successful step.