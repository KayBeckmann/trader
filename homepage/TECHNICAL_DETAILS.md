# Technische Dokumentation - Trader System

## Inhaltsverzeichnis

1. [Projektstruktur](#projektstruktur)
2. [Backend-Architektur](#backend-architektur)
3. [Frontend-Architektur](#frontend-architektur)
4. [Datenfluss](#datenfluss)
5. [Neural Network Implementation](#neural-network-implementation)
6. [WebSocket-Kommunikation](#websocket-kommunikation)
7. [Nginx-Konfiguration](#nginx-konfiguration)

---

## Projektstruktur

```
trader/
├── backend/
│   ├── proj/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── knn.py           # KNN-Vorhersagen Endpunkt
│   │   │   │   ├── trades.py        # Trades Endpunkt
│   │   │   │   ├── market.py        # Marktzeiten Endpunkt
│   │   │   │   ├── metrics.py       # Metriken Endpunkt
│   │   │   │   └── websocket.py     # WebSocket Handler
│   │   │   ├── services/
│   │   │   │   ├── knn_service.py   # ML-Service
│   │   │   │   └── neural_network.py# Neural Network
│   │   │   ├── database.py          # DB-Verbindung
│   │   │   ├── models.py            # SQLAlchemy Models
│   │   │   └── main.py              # FastAPI App
│   │   ├── celery.py                # Celery Konfiguration
│   │   ├── tasks.py                 # Datenerfassung Tasks
│   │   └── trading_tasks.py         # Trading Tasks
│   ├── stocks.txt                   # Symbol-Liste
│   ├── requirements.txt             # Python Dependencies
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.vue                  # Hauptkomponente
│   │   └── main.js                  # Vue Entry Point
│   ├── nginx.conf                   # Nginx Konfiguration
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── homepage/
│   ├── README.md                    # Projektübersicht
│   └── TECHNICAL_DETAILS.md         # Diese Datei
│
├── docker-compose.yml
├── stocks.txt                       # Symbol-Liste (Root)
└── .env                             # Umgebungsvariablen
```

---

## Backend-Architektur

### FastAPI Application (main.py)

```python
# Startup-Ablauf:
1. Datenbankverbindung herstellen
2. Tabellen erstellen (create_all)
3. Migrationen ausführen (score-Spalte)
4. Redis-Listener für WebSocket starten
5. API-Router registrieren
```

### API-Router

#### `/api/knn/top` (knn.py)

Gibt die neuesten ML-Vorhersagen zurück:

```python
# Response-Format:
{
    "long": [
        {"id": 1, "symbol": "NVDA", "rank": 1, "score": 0.85},
        ...
    ],
    "short": [
        {"id": 11, "symbol": "META", "rank": 1, "score": 0.78},
        ...
    ]
}
```

#### `/api/trades` (trades.py)

Gibt alle geschlossenen Trades zurück:

```python
# Response: Liste von Trade-Objekten
[
    {
        "id": 1,
        "symbol": "AAPL",
        "type": "long",
        "entry_price": 150.00,
        "exit_price": 165.00,
        "status": "closed",
        "result": 1,
        "created_at": "2024-01-01T10:00:00",
        "closed_at": "2024-01-01T11:00:00"
    }
]
```

### Celery Tasks

#### Datenerfassung (tasks.py)

```python
@app.task
def fetch_and_store_stock_data():
    """
    - Liest Symbole aus stocks.txt
    - Filtert bereits blockierte Symbole (3+ Fehler)
    - Ruft Kurse über yfinance ab
    - Speichert in stock_prices Tabelle
    - Aktualisiert Fehler-Counter bei Misserfolg
    """
```

#### Trading Tasks (trading_tasks.py)

```python
@app.task
def open_trades():
    """Eröffnet Long/Short Positionen für alle Symbole"""

@app.task
def evaluate_trades():
    """
    Prüft offene Trades auf:
    - Take-Profit: >= +10%
    - Stop-Loss: <= -10%
    - Timeout: > 1 Stunde
    """

@app.task
def generate_knn_predictions():
    """
    1. Trainiert Neural Network (falls nötig)
    2. Generiert Vorhersagen für alle Symbole
    3. Speichert in DB
    4. Publiziert über Redis
    """
```

---

## Frontend-Architektur

### Vue.js 3 Composition API

```javascript
// Reaktive State-Variablen
const topLong = ref([]);        // Top 10 Long Vorhersagen
const topShort = ref([]);       // Top 10 Short Vorhersagen
const dataLoading = ref(true);  // Ladezustand Vorhersagen
const tradesLoading = ref(true);// Ladezustand Trades
const wsConnected = ref(false); // WebSocket Status
const chartData = ref({...});   // Chart.js Daten

// Computed Properties
const hasTradeData = computed(() => {...}); // Prüft ob Trades vorhanden
const connectionStatus = computed(() => {...}); // WS Status Text
```

### Datenabfrage

```javascript
// Initial beim Mount
onMounted(() => {
    fetchTopKnnResults();  // HTTP GET /api/knn/top
    fetchTradeHistory();   // HTTP GET /api/trades
    connectWebSocket();    // WS /ws/predictions

    // Polling alle 60 Sekunden
    setInterval(() => {
        fetchTradeHistory();
        if (!wsConnected.value) {
            fetchTopKnnResults(); // Fallback wenn WS down
        }
    }, 60000);
});
```

### Chart.js Konfiguration

```javascript
// Profit/Loss Chart
chartData.value = {
    datasets: [{
        label: 'Profit/Loss',
        backgroundColor: '#f87979',
        borderColor: '#f87979',
        data: trades.map(trade => ({
            x: new Date(trade.closed_at),
            y: (trade.exit_price - trade.entry_price) *
               (trade.type === 'long' ? 1 : -1)
        }))
    }]
};

// X-Achse: Zeit (Stunden)
// Y-Achse: Profit/Loss in Währungseinheiten
```

---

## Datenfluss

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATENFLUSS                                │
└─────────────────────────────────────────────────────────────────┘

1. DATENERFASSUNG (jede Minute)
   ┌──────────┐      ┌──────────┐      ┌──────────────┐
   │ stocks.  │ ──▶  │ yfinance │ ──▶  │ stock_prices │
   │   txt    │      │   API    │      │    Tabelle   │
   └──────────┘      └──────────┘      └──────────────┘

2. TRADE-GENERIERUNG (alle 5 Minuten)
   ┌──────────────┐      ┌────────────────────────────┐
   │ stock_prices │ ──▶  │ trades (status='open')     │
   │  (neueste)   │      │ Long + Short für jedes     │
   └──────────────┘      │ Symbol                     │
                         └────────────────────────────┘

3. TRADE-EVALUATION (alle 30 Sekunden)
   ┌─────────────────┐      ┌─────────────────────────┐
   │ trades (open)   │ ──▶  │ Prüfe:                  │
   │ + aktuelle      │      │ - PnL >= +10% → Gewinn  │
   │   Kurse         │      │ - PnL <= -10% → Verlust │
   └─────────────────┘      │ - Zeit > 1h → Neutral   │
                            └─────────────────────────┘
                                       │
                                       ▼
                            ┌─────────────────────────┐
                            │ trades (status='closed')│
                            │ result = 1/-1/0         │
                            └─────────────────────────┘

4. ML-TRAINING & VORHERSAGE (jede Minute)
   ┌─────────────────┐      ┌─────────────────────────┐
   │ trades (closed) │ ──▶  │ Feature Extraction:     │
   │ + stock_prices  │      │ - price_change_1h       │
   └─────────────────┘      │ - price_change_24h      │
                            │ - volatility            │
                            │ - volume_ratio          │
                            └───────────┬─────────────┘
                                        │
                                        ▼
                            ┌─────────────────────────┐
                            │   Neural Network        │
                            │   Training & Predict    │
                            └───────────┬─────────────┘
                                        │
                          ┌─────────────┴─────────────┐
                          ▼                           ▼
              ┌─────────────────┐         ┌─────────────────┐
              │   knn_results   │         │  Redis Publish  │
              │    Tabelle      │         │ 'predictions'   │
              └─────────────────┘         └────────┬────────┘
                                                   │
5. FRONTEND-UPDATE                                 │
                                                   ▼
              ┌─────────────────┐         ┌─────────────────┐
              │   REST API      │◀────────│   WebSocket     │
              │  /api/knn/top   │         │ /ws/predictions │
              └────────┬────────┘         └────────┬────────┘
                       │                           │
                       └───────────┬───────────────┘
                                   ▼
                       ┌─────────────────────────┐
                       │      Vue.js Frontend    │
                       │   Dashboard aktualisiert│
                       └─────────────────────────┘
```

---

## Neural Network Implementation

### Architektur (neural_network.py)

```python
class NeuralNetwork:
    def __init__(self, input_size=4, hidden_sizes=[16, 8], output_size=2):
        # Xavier/He Initialisierung
        self.weights = [...]
        self.biases = [...]

    def forward(self, X):
        """Forward Pass mit ReLU Aktivierung"""
        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            X = X @ W + b
            if i < len(self.weights) - 1:
                X = self.relu(X)  # Hidden Layers
            else:
                X = self.softmax(X)  # Output Layer
        return X

    def backward(self, X, y, learning_rate):
        """Backpropagation mit Gradient Descent"""
        # Berechne Gradienten
        # Update Weights und Biases
```

### Training Loop

```python
def train(self, X, y, epochs=100, learning_rate=0.01):
    losses = []
    for epoch in range(epochs):
        # Forward Pass
        predictions = self.forward(X)

        # Loss berechnen (Cross-Entropy)
        loss = -np.mean(y * np.log(predictions + 1e-8))
        losses.append(loss)

        # Backward Pass
        self.backward(X, y, learning_rate)

    return losses
```

### Feature Engineering (knn_service.py)

```python
def _get_training_data(self):
    """
    Für jeden geschlossenen Trade:
    1. Hole Preise um den Trade-Zeitpunkt
    2. Berechne Features:
       - price_change_1h: (aktuell - vor_1h) / vor_1h
       - price_change_24h: (aktuell - vor_24h) / vor_24h
       - volatility: std(preise_24h) / mean(preise_24h)
       - volume_ratio: datenpunkte_1h / (datenpunkte_24h / 24)
    3. Label: 1 wenn profitabel, 0 sonst
    """
```

---

## WebSocket-Kommunikation

### Backend (websocket.py)

```python
# Redis Subscriber läuft als Background Task
async def redis_listener():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('predictions')

    async for message in pubsub.listen():
        if message['type'] == 'message':
            # Broadcast an alle verbundenen Clients
            for client in connected_clients:
                await client.send_json(message['data'])

# WebSocket Endpoint
@router.websocket("/ws/predictions")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_text('pong')
    finally:
        connected_clients.remove(websocket)
```

### Frontend (App.vue)

```javascript
const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/predictions`;

    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.long && data.short) {
            topLong.value = data.long.map(...);
            topShort.value = data.short.map(...);
        }
    };

    // Heartbeat alle 25 Sekunden
    heartbeatInterval = setInterval(() => {
        ws.send('ping');
    }, 25000);

    // Auto-Reconnect bei Disconnect
    ws.onclose = () => {
        setTimeout(connectWebSocket, 5000);
    };
};
```

---

## Nginx-Konfiguration

### nginx.conf (Frontend Container)

```nginx
server {
    listen 80;
    server_name localhost;

    # Statische Dateien (Vue.js Build)
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API Proxy → Backend Container
    location /api/ {
        resolver 127.0.0.11 valid=30s;
        set $backend_upstream trader_backend:8000;
        proxy_pass http://$backend_upstream$request_uri;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket Proxy
    location /ws/ {
        resolver 127.0.0.11 valid=30s;
        set $backend_upstream trader_backend:8000;
        proxy_pass http://$backend_upstream$request_uri;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### Wichtige Konfigurationen

| Einstellung | Zweck |
|-------------|-------|
| `resolver 127.0.0.11` | Docker DNS für Service Discovery |
| `$request_uri` | Vollständiger Pfad inkl. Query Params |
| `proxy_read_timeout 86400` | WebSocket 24h offen halten |
| `Upgrade/Connection` | WebSocket Protokoll-Upgrade |

---

## Fehlerbehandlung

### Symbol Failure Tracking

```python
# Bei 3+ Fehlern wird Symbol blockiert
if failure_count >= 3:
    # Symbol wird nicht mehr abgefragt
    # Täglich um Mitternacht: Entfernung aus stocks.txt
```

### Fallback-Predictions

```python
def _generate_fallback_predictions(self, symbols):
    """
    Wenn ML-Training fehlschlägt:
    1. Versuche Symbole aus stocks.txt zu laden
    2. Generiere zufällige Scores (0.5-0.8)
    3. Gib Top 10 Long/Short zurück
    """
```

### Frontend Error States

```vue
<!-- Wenn keine Daten vorhanden -->
<div v-if="topLong.length === 0" class="no-data">
    <p>No predictions available</p>
    <small>System needs time to collect data and train the model.</small>
</div>
```

---

## Performance-Optimierungen

1. **Datenbank-Indizes**: `symbol` und `created_at` indiziert
2. **Connection Pooling**: SQLAlchemy Session Management
3. **Redis Pub/Sub**: Echtzeitkommunikation ohne Polling
4. **Nginx Caching**: Statische Assets gecached
5. **Docker Volumes**: Persistente Daten, schneller Container-Restart
