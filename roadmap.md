# Trader – Roadmap

> **Dieses Projekt ist ein reines Schulungs- und Forschungsprojekt.**
> Die angezeigten Informationen stellen **keine Anlageberatung** dar.
> Alle Signale sind experimentell und dienen ausschließlich Lernzwecken.

---

## Phase 1 – Fundament & Infrastruktur ✅

Ziel: Lauffähige Docker-Umgebung mit Datenbank und erstem Datenabruf.

- [x] Projektstruktur anlegen (`backend/`, `worker/`, `frontend/`, `db/`)
- [x] `docker-compose.yml` mit allen 4 Containern definieren:
  - `db` – PostgreSQL mit persistentem Volume
  - `backend` – FastAPI
  - `worker` – Scheduler + KNN
  - `frontend` – Nginx mit statischen Dateien
- [x] Gemeinsames Docker-Netzwerk konfigurieren
- [x] `.env`-Datei für Umgebungsvariablen (DB-Credentials, Konfiguration)
- [x] PostgreSQL-Schema anlegen:
  - Tabelle `kurse` (`id`, `timestamp`, `aktie`, `wert`)
  - Tabelle `trades` (alle Felder inkl. Gebühren und Reward)
  - Aggregierte View `statistik` je Aktie

**Meilenstein:** `docker-compose up` startet alle Container ohne Fehler, Datenbank ist erreichbar. ✅

---

## Phase 2 – Datenabruf & Speicherung ✅

Ziel: Kursdaten werden automatisch alle 5 Minuten abgerufen und gespeichert.

- [x] yfinance-Integration im `worker`-Container (`pip install yfinance`)
- [x] Ticker-Liste der 90 MSCI-ACWI-Titel hinterlegen (6 Sektoren)
- [x] Batch-Abruf aller Ticker: `yf.download(tickers=[...], interval="5m", period="1d")`
- [x] Handelszeiten-Check implementieren (NYSE: Mo–Fr 15:30–22:00 Uhr MEZ)
- [x] APScheduler: Job alle 5 Minuten, außerhalb der Handelszeiten überspringen
- [x] Abgerufene Kurse in Tabelle `kurse` schreiben
- [x] Fehlerbehandlung: Retry-Logik bei API-Ausfällen, Logging
- [x] Historische Kursdaten initial laden (Backfill, max. 60 Tage bei 5m-Auflösung)

**Meilenstein:** Datenbank füllt sich automatisch während der Handelszeiten mit 5-Minuten-Kursen aller 90 Titel. ✅

---

## Phase 3 – Datenaufbereitung (Feature Engineering) ✅

Ziel: Rohdaten werden zu normalisierten Feature-Vektoren für das KNN aufbereitet.

- [x] Relativen Kurswert berechnen (aktuell vs. Vergangenheit):
  - Gestiegen → positiver Wert bis `+1`
  - Gefallen → negativer Wert bis `-1`
  - Unverändert → `0`
- [x] Min-Max-Skalierung auf `[-1, 1]` über rollendes 7-Tage-Fenster
- [x] Drei Deltas je Aktie berechnen:
  - `delta_5m` – Veränderung der letzten 5 Minuten
  - `delta_20m` – Veränderung der letzten 20 Minuten
  - `delta_60m` – Veränderung der letzten 60 Minuten
- [x] Feature-Vektor je Aktie: `[delta_5m, delta_20m, delta_60m]`
- [x] Alle Aktien zu gemeinsamem Eingabe-Tensor zusammenführen (90 × 3)

**Meilenstein:** Für jeden 5-Minuten-Takt wird ein vollständiger, normalisierter Eingabe-Tensor erzeugt. ✅

---

## Phase 4 – KNN & Inferenz ✅

Ziel: Das neuronale Netz verarbeitet alle Aktien parallel und gibt Empfehlungen aus.

- [x] KNN-Architektur implementieren:
  - Eingabe: Tensor `[90 Aktien × 3 Zeitfenster]` (flach: 270 Neuronen)
  - Versteckte Schichten (Größe und Anzahl nach Experiment)
  - Ausgabe: 90 Werte im Bereich `[-1, 1]` via `tanh`
- [x] Alle Aktien werden parallel verarbeitet (kein sequenzieller Loop)
- [x] Ausgabewerte nach Stärke sortieren:
  - Top 10 Long-Kandidaten (höchste positive Werte)
  - Top 10 Short-Kandidaten (stärkste negative Werte)
- [x] Modell-Checkpoints in Docker-Volume speichern
- [x] Erstes Training mit zufälligen Gewichten (Bootstrap)

**Meilenstein:** KNN läuft durch, erzeugt für jeden Takt eine Top-10-Long- und Top-10-Short-Liste. ✅

---

## Phase 5 – Virtuelles Trading & Reinforcement Learning ✅

Ziel: KNN-Empfehlungen werden als virtuelle Trades ausgeführt und das Ergebnis trainiert das Modell.

- [x] Virtuellen Trade-Manager implementieren:
  - Einsatz: 100 € pro Trade
  - Gebühr Eröffnung: 0,5% auf Einsatz (= 0,50 €)
  - Gebühr Schließung: 0,5% auf aktuellen Positionswert
  - Stop-Loss bei -15% (netto nach Gebühren)
  - Take-Profit bei +15% (netto nach Gebühren)
  - Timeout nach 1 Stunde
- [x] Trade-Ergebnis in Tabelle `trades` schreiben
- [x] Reward-Berechnung:
  - Take-Profit → `reward = +1`
  - Stop-Loss → `reward = -1`
  - Timeout, `|ergebnis| ≥ 10 €` → proportionaler Reward
  - Timeout, `|ergebnis| < 10 €` → `reward = null` (ignoriert)
- [x] Reward-Signal ans KNN zurückgeben (Reinforcement Learning)
- [x] Trainingsloop: Nach jedem abgeschlossenen Trade Modell aktualisieren

**Meilenstein:** Das KNN lernt kontinuierlich aus seinen eigenen virtuellen Trades. ✅

---

## Phase 6 – REST API ✅

Ziel: Backend stellt alle nötigen Daten für das Frontend bereit.

- [x] `GET /empfehlungen` – aktuelle Top-10-Long- und Top-10-Short-Liste mit KNN-Wert
- [x] `GET /statistik` – Trefferquote, Gesamtergebnis, Anzahl Trades je Aktie
- [x] `GET /statistik/gesamt` – aggregierte KNN-Performance über alle Aktien
- [x] `GET /kurse?aktie=AAPL` – Kursverlauf einer Aktie für Chart

**Meilenstein:** Alle API-Endpunkte liefern valide JSON-Antworten. ✅

---

## Phase 7 – Frontend ✅

Ziel: Dashboard zeigt Empfehlungen, Statistiken und Kursverläufe übersichtlich an.

- [x] `index.html` als Single-Page-Dashboard (HTML + Vanilla JS + CSS)
- [x] Kein Build-Schritt, Chart.js via CDN
- [x] Dauerhaft sichtbarer Disclaimer (nicht wegklickbar)
- [x] Top-10-Long-Tabelle mit KNN-Gewichtung (Balken/Farbskala)
- [x] Top-10-Short-Tabelle mit KNN-Gewichtung (Balken/Farbskala)
- [x] Je Aktie: Trefferquote, kumuliertes Ergebnis in €, Anzahl Trades
- [x] Gesamtstatistik des KNN (Portfolio-Sicht)
- [x] Kursverlauf-Chart für ausgewählte Aktie (Chart.js)
- [x] Automatische Aktualisierung alle 5 Minuten via `setInterval`

**Meilenstein:** Dashboard läuft im Browser, aktualisiert sich automatisch, zeigt alle Kennzahlen. ✅

---

## Phase 8 – Stabilisierung & Feinschliff

Ziel: System läuft stabil über mehrere Handelstage, Qualität wird verbessert.

- [ ] Logging in allen Containern vereinheitlichen
- [ ] Fehlerbehandlung für Edge Cases (fehlende Kurse, DB-Verbindungsabbruch)
- [ ] Modell-Performance evaluieren (Trefferquote über Zeit beobachten)
- [ ] KNN-Hyperparameter anpassen (Lernrate, Schichtgröße, Aktivierungsfunktionen)
- [ ] Backtesting auf historischen Daten durchführen

**Meilenstein:** System läuft mehrere Tage ohne manuelle Eingriffe stabil durch.

---

## Technologie-Übersicht

| Bereich         | Technologie                        | Container    |
|-----------------|------------------------------------|--------------|
| Backend / API   | Python, FastAPI                    | `backend`    |
| ML / Scheduler  | PyTorch, Scikit-learn, APScheduler | `worker`     |
| Datenabruf      | yfinance                           | `worker`     |
| Datenbank       | PostgreSQL, SQLAlchemy             | `db`         |
| Frontend        | HTML, Vanilla JS, Chart.js (CDN)   | `frontend`   |
| Webserver       | Nginx                              | `frontend`   |
| Deployment      | Docker, docker-compose             | –            |
