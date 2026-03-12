# Trader – KI-gestützte Aktienanalyse

> **Dieses Projekt ist ein reines Schulungs- und Forschungsprojekt.**
> Die angezeigten Informationen stellen **keine Anlageberatung** dar.
> Alle Signale sind experimentell und dienen ausschließlich Lernzwecken.

---

## Projektbeschreibung

Trader ist ein modulares System, das Aktienkurse von 90 MSCI-ACWI-Titeln automatisch alle 5 Minuten abruft, per neuronalem Netz (KNN) auswertet und die Ergebnisse in einem Web-Dashboard visualisiert. Das KNN lernt kontinuierlich durch virtuelles Trading (Reinforcement Learning) – es werden nie echte Trades ausgeführt.

## Architektur

```
┌─────────────────────────────────────────────────┐
│                  trader_net (Bridge)             │
│                                                  │
│  ┌──────────┐   REST API   ┌──────────────────┐  │
│  │ frontend │─────────────▶│    backend       │  │
│  │  (Nginx) │              │   (FastAPI)      │  │
│  └──────────┘              └────────┬─────────┘  │
│                                     │            │
│                            ┌────────▼─────────┐  │
│  ┌──────────┐              │       db         │  │
│  │  worker  │─────────────▶│  (PostgreSQL)    │  │
│  │(APSched.)│              └──────────────────┘  │
│  └──────────┘                                    │
└─────────────────────────────────────────────────┘
```

| Container        | Technologie                          | Aufgabe                                      |
|------------------|--------------------------------------|----------------------------------------------|
| `db`             | PostgreSQL 16                        | Kursdaten, Trades, Statistiken               |
| `backend`        | Python, FastAPI                      | REST API für das Frontend                    |
| `worker`         | Python, APScheduler, PyTorch         | Datenabruf (yfinance), KNN, virtuelles Trading |
| `frontend`       | Nginx, HTML, Vanilla JS, Chart.js    | Web-Dashboard                                |

## Voraussetzungen

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2

## Schnellstart

```bash
# Repository klonen
git clone https://github.com/KayBeckmann/trader.git
cd trader

# Umgebungsvariablen anlegen
cp .env.example .env
# .env nach Bedarf anpassen (mindestens POSTGRES_PASSWORD setzen)

# Container bauen und starten
docker-compose up --build
```

| Dienst   | URL                        |
|----------|----------------------------|
| Frontend | http://localhost           |
| API      | http://localhost:8000      |
| API-Docs | http://localhost:8000/docs |

## Konfiguration

Die Datei `.env` steuert alle Umgebungsvariablen:

| Variable            | Beschreibung                   | Beispielwert |
|---------------------|--------------------------------|--------------|
| `POSTGRES_DB`       | Name der Datenbank             | `trader`     |
| `POSTGRES_USER`     | Datenbankbenutzer              | `trader`     |
| `POSTGRES_PASSWORD` | Datenbankpasswort (**ändern!**) | `changeme`   |

## Datenbankschema

### Tabelle `kurse`
Speichert jeden abgerufenen 5-Minuten-Kurs.

| Spalte      | Typ            | Beschreibung                  |
|-------------|----------------|-------------------------------|
| `id`        | BIGSERIAL PK   | Primärschlüssel               |
| `timestamp` | TIMESTAMPTZ    | Zeitpunkt des Abrufs          |
| `aktie`     | VARCHAR(20)    | Ticker-Symbol (z. B. `AAPL`) |
| `wert`      | NUMERIC(18, 6) | Kurs zum Abrufzeitpunkt       |

### Tabelle `trades`
Protokolliert jeden virtuellen Trade inkl. Gebühren und Reward.

| Spalte                    | Typ           | Beschreibung                                  |
|---------------------------|---------------|-----------------------------------------------|
| `id`                      | BIGSERIAL PK  | Primärschlüssel                               |
| `aktie`                   | VARCHAR(20)   | Ticker-Symbol                                 |
| `richtung`                | VARCHAR(5)    | `long` oder `short`                           |
| `eroeffnet_at`            | TIMESTAMPTZ   | Eröffnungszeitpunkt                           |
| `geschlossen_at`          | TIMESTAMPTZ   | Schlusszeitpunkt                              |
| `schliessgrund`           | VARCHAR(20)   | `stop_loss`, `take_profit` oder `timeout`     |
| `einsatz_eur`             | NUMERIC(10,2) | Virtueller Einsatz (100 €)                    |
| `gebuehr_eroeffnung_eur`  | NUMERIC(10,4) | Eröffnungsgebühr (0,5 % auf Einsatz)          |
| `gebuehr_schliessung_eur` | NUMERIC(10,4) | Schließungsgebühr (0,5 % auf Positionswert)   |
| `ergebnis_eur`            | NUMERIC(10,4) | Nettoergebnis in € nach Gebühren              |
| `reward`                  | NUMERIC(5,4)  | RL-Signal (−1 bis +1, oder NULL)              |

### View `statistik`
Aggregierte Kennzahlen je Aktie (nur abgeschlossene Trades).

## Ticker-Universum

90 Titel aus 6 Sektoren (MSCI ACWI, US-gelistet):

| Sektor              | Ticker                                                             |
|---------------------|--------------------------------------------------------------------|
| Technologie         | AAPL MSFT NVDA AMZN META GOOGL TSLA AVGO ORCL AMD NFLX CRM INTC CSCO IBM QCOM TXN ADBE NOW INTU |
| Finanzen            | JPM BAC GS MS V MA BLK AXP WFC C                                  |
| Gesundheit          | LLY UNH JNJ MRK ABBV ABT TMO DHR AMGN ISRG                       |
| Energie & Industrie | XOM CVX GE CAT DE LMT RTX BA HON UPS                             |
| Konsumgüter         | WMT COST HD MCD PG KO PEP SBUX NKE TGT                           |
| International (ADR) | TSM ASML NVO SAP TTE SHEL SNY AZN RIO UL                         |

## API-Endpunkte (geplant)

| Methode | Pfad                  | Beschreibung                                      |
|---------|-----------------------|---------------------------------------------------|
| GET     | `/health`             | Healthcheck                                       |
| GET     | `/empfehlungen`       | Top-10-Long- und Top-10-Short-Liste mit KNN-Wert  |
| GET     | `/statistik`          | Trefferquote und Ergebnis je Aktie                |
| GET     | `/statistik/gesamt`   | Aggregierte KNN-Performance über alle Aktien      |
| GET     | `/kurse?aktie=AAPL`   | Kursverlauf einer Aktie für den Chart             |

## Roadmap

| Phase | Inhalt                              | Status        |
|-------|-------------------------------------|---------------|
| 1     | Fundament & Infrastruktur           | ✅ Abgeschlossen |
| 2     | Datenabruf & Speicherung            | 🔜 Geplant    |
| 3     | Feature Engineering                 | 🔜 Geplant    |
| 4     | KNN & Inferenz                      | 🔜 Geplant    |
| 5     | Virtuelles Trading & RL             | 🔜 Geplant    |
| 6     | REST API                            | 🔜 Geplant    |
| 7     | Frontend-Dashboard                  | 🔜 Geplant    |
| 8     | Stabilisierung & Feinschliff        | 🔜 Geplant    |

Details: [roadmap.md](roadmap.md)

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
