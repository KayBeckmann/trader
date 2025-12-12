# Trader - ML-basiertes Aktienanalyse-System

## Projektübersicht

**Trader** ist ein automatisiertes Trading-Analyse-System, das Machine Learning verwendet, um Kauf- und Verkaufssignale für Aktien zu generieren. Das System sammelt kontinuierlich Marktdaten, trainiert ein neuronales Netzwerk auf Basis historischer Trade-Ergebnisse und generiert Echtzeit-Vorhersagen.

### Hauptfunktionen

- **Automatische Datenerfassung**: Sammelt Aktienkurse von über 1.200 Symbolen weltweit
- **Virtuelles Trading**: Simuliert Long- und Short-Positionen zur Modelltraining
- **ML-Vorhersagen**: Neuronales Netzwerk für Kauf-/Verkaufssignale
- **Echtzeit-Dashboard**: WebSocket-basierte Live-Updates der Vorhersagen
- **Trade History**: Visualisierung der Performance über Zeit

---

## Architektur

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│                     (Vue.js 3 + Nginx)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │  Top 10     │  │  Top 10     │  │     Trade History Chart     │  │
│  │   Long      │  │   Short     │  │      (Profit/Loss)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
│         │                │                        │                  │
│         └────────────────┼────────────────────────┘                  │
│                          │                                           │
│                    WebSocket / REST API                              │
└──────────────────────────┼───────────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────────────┐
│                      BACKEND (FastAPI)                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │
│  │ /api/knn   │  │ /api/trades│  │ /api/      │  │    /ws/    │     │
│  │   /top     │  │            │  │  metrics   │  │ predictions│     │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────────────┐
│                    BACKGROUND WORKERS                                │
│                     (Celery + Beat)                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐     │
│  │ Datenerfassung │  │ Trade-Manager  │  │  KNN-Prediction    │     │
│  │  (1 min)       │  │  (30 sek)      │  │   Generator (1 min)│     │
│  └────────────────┘  └────────────────┘  └────────────────────┘     │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────────────┐
│                      DATENSCHICHT                                    │
│        ┌─────────────────┐        ┌─────────────────┐               │
│        │   PostgreSQL    │        │      Redis      │               │
│        │   (Persistenz)  │        │ (Message Broker)│               │
│        └─────────────────┘        └─────────────────┘               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Technische Details

### Tech-Stack

| Komponente | Technologie | Version |
|------------|-------------|---------|
| Frontend | Vue.js 3 (Composition API) | 3.x |
| Build Tool | Vite | 4.x |
| Charts | Chart.js + vue-chartjs | 4.x |
| Web Server | Nginx | Alpine |
| Backend | FastAPI | 0.100+ |
| ASGI Server | Uvicorn | 0.23+ |
| Task Queue | Celery | 5.x |
| Scheduler | Celery Beat | 5.x |
| Datenbank | PostgreSQL | 13 |
| Cache/Broker | Redis | 7 |
| ML Framework | NumPy (Custom Neural Network) | 1.24+ |
| Datenquelle | yfinance | 0.2+ |
| Container | Docker + Docker Compose | 24.x |

### Datenbank-Schema

```sql
-- Aktienkurse
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    price FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Virtuelle Trades
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    type ENUM('long', 'short') NOT NULL,
    entry_price FLOAT NOT NULL,
    exit_price FLOAT,
    status ENUM('open', 'closed') DEFAULT 'open',
    result INTEGER,  -- 1=Gewinn, -1=Verlust, 0=Neutral
    created_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP
);

-- ML-Vorhersagen
CREATE TABLE knn_results (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    type ENUM('long', 'short') NOT NULL,
    rank INTEGER NOT NULL,
    score FLOAT,  -- Konfidenzwert (0-1)
    created_at TIMESTAMP DEFAULT NOW()
);

-- Fehlerhafte Symbole
CREATE TABLE symbol_failures (
    symbol VARCHAR PRIMARY KEY,
    failure_count INTEGER DEFAULT 0,
    last_attempt TIMESTAMP DEFAULT NOW()
);
```

### API-Endpunkte

| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/knn/top` | GET | Top 10 Long/Short Vorhersagen |
| `/api/trades` | GET | Liste aller geschlossenen Trades |
| `/api/metrics` | GET | System-Metriken und Statistiken |
| `/api/health` | GET | Health-Check |
| `/api/market-hours` | GET | Marktöffnungszeiten |
| `/ws/predictions` | WebSocket | Echtzeit-Vorhersagen |

### Scheduled Tasks (Celery Beat)

| Task | Intervall | Beschreibung |
|------|-----------|--------------|
| `fetch_and_store_stock_data` | 1 Minute | Aktienkurse von Yahoo Finance abrufen |
| `open_trades` | 5 Minuten | Virtuelle Long/Short Positionen eröffnen |
| `evaluate_trades` | 30 Sekunden | Offene Trades prüfen und schließen |
| `generate_knn_predictions` | 1 Minute | ML-Vorhersagen generieren |
| `create_knn_trades` | 1 Minute | Trades basierend auf Vorhersagen |
| `remove_failed_stocks` | Täglich 00:00 | Fehlerhafte Symbole entfernen |

---

## Machine Learning Pipeline

### Neuronales Netzwerk

Das System verwendet ein selbst implementiertes Feed-Forward Neural Network:

```
Input Layer (4 Features)
        │
        ▼
Hidden Layer 1 (16 Neuronen, ReLU)
        │
        ▼
Hidden Layer 2 (8 Neuronen, ReLU)
        │
        ▼
Output Layer (2 Klassen, Softmax)
```

### Features

| Feature | Beschreibung |
|---------|--------------|
| `price_change_1h` | Preisänderung letzte Stunde (%) |
| `price_change_24h` | Preisänderung letzte 24 Stunden (%) |
| `volatility` | Standardabweichung / Mittelwert (24h) |
| `volume_ratio` | Verhältnis 1h-Datenpunkte zu 24h-Durchschnitt |

### Training

- **Trainingsdaten**: Geschlossene Trades mit bekanntem Ergebnis
- **Mindestdaten**: 10 geschlossene Trades
- **Label**: Binär (1 = Profitabel, 0 = Nicht profitabel)
- **Lernrate**: 0.01
- **Epochen**: 100

### Trade-Logik

Virtuelle Positionen werden geschlossen wenn:
- **Take-Profit**: +10% Gewinn
- **Stop-Loss**: -10% Verlust
- **Timeout**: Nach 1 Stunde

---

## Docker-Services

```yaml
services:
  postgres:      # Datenbank (Port 5432)
  redis:         # Message Broker (Port 6379)
  backend:       # FastAPI Server (Port 8000 intern)
  worker:        # Celery Worker
  beat:          # Celery Beat Scheduler
  frontend:      # Nginx + Vue.js (Port 80)
```

### Volumes

- `postgres_data`: Persistente Datenbankdaten

### Umgebungsvariablen (.env)

```bash
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=trader
DATABASE_URL=postgresql://user:password@postgres:5432/trader
REDIS_URL=redis://redis:6379/0
FRONTEND_PORT=80
```

---

## Datenquellen

### Aktienliste (stocks.txt)

Das System überwacht über **1.200 Symbole** aus verschiedenen Märkten:

- **US-Märkte**: NASDAQ, NYSE (AAPL, MSFT, NVDA, etc.)
- **Europäische Märkte**: DAX, FTSE, CAC (SAP, NESN, ASML, etc.)
- **Asiatische Märkte**: TSE, HKEX, KRX (7203, 700, 005930, etc.)
- **Krypto**: BTC, ETH

### Datenformat

```
NVDA,stock
MSFT,stock
BTC,crypto
```

---

## Systemanforderungen

### Minimum

- Docker 20.x+
- Docker Compose 2.x+
- 2 GB RAM
- 10 GB Speicher

### Empfohlen

- 4+ GB RAM
- SSD-Speicher
- Stabile Internetverbindung

---

## Installation & Start

```bash
# Repository klonen
git clone <repository-url>
cd trader

# Umgebungsvariablen konfigurieren
cp .env.example .env

# Container starten
docker-compose up -d --build

# Logs ansehen
docker-compose logs -f
```

### Anlaufzeit

Das System benötigt eine **Anlaufzeit von 1-2 Stunden**, um:
1. Initiale Aktienkurse zu sammeln
2. Virtuelle Trades zu eröffnen und abzuschließen
3. Das ML-Modell mit genügend Daten zu trainieren

---

## Monitoring

### Backend-Logs

```bash
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f beat
```

### Metriken-Endpunkt

```bash
curl http://localhost/api/metrics
```

Liefert:
- Anzahl Trades
- Win-Rate
- Aktive Symbole
- System-Status

---

## Bekannte Einschränkungen

1. **Keine echten Trades**: Nur Analyse und Simulation
2. **Yahoo Finance Rate Limits**: Bei vielen Symbolen möglich
3. **Marktzeiten**: Keine Echtzeit-Daten außerhalb der Börsenzeiten
4. **ML-Genauigkeit**: Hängt von Datenqualität und Marktbedingungen ab

---

## Lizenz

Privates Projekt - Alle Rechte vorbehalten.

---

## Kontakt

Bei Fragen oder Problemen: Issue im Repository erstellen.
