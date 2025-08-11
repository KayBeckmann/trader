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
    - **Backend:** Python, FastAPI
    - **Database:** PostgreSQL (confirmed from start)
    - **Neural Network:** STRICTLY from scratch using NumPy. NO TensorFlow, PyTorch, or other frameworks. Activation: tanh. Random weight initialization.
    - **Frontend:** Vue.js 3 (responsive)
- **Deployment:**
    - Docker-first approach.
    - Separate containers for each service (Backend, Frontend, DB).
    - Managed via Docker Compose.
- **Web UI Features:**
    - Display top 10 long/short lists.
    - Display P/L graph.
    - Display market opening hours, converted to user's timezone.
    - **Internal Wiki:** A section in the frontend for documenting the application's functionality and architecture.