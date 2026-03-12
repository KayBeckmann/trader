# Trader – Todo & Projektideen

## Projektziel
Ein modulares System, das Aktienkurse analysiert, per KI Prognosen erstellt und Ergebnisse übersichtlich darstellt.

---

## Kernfunktionen

### Datenbeschaffung
- [ ] Aktienkurse automatisch alle 5 Minuten abrufen (Hintergrundjob / Scheduler)
- [ ] Abruf-Intervall konfigurierbar halten (Standard: 5 min)
- [ ] Historische Kursdaten initial laden (Backfill)
- [ ] Fehlerbehandlung bei API-Ausfällen (Retry-Logik, Logging)

### Datenbank
- [ ] SQL-Datenbank aufsetzen
- [ ] Tabelle `kurse` definieren:
  - `id` – Primärschlüssel
  - `datum` – Datum des Abrufs
  - `uhrzeit` – Uhrzeit des Abrufs
  - `aktie` – Tickersymbol (z.B. AAPL, TSLA)
  - `wert` – Kurs zum Abrufzeitpunkt
- [ ] Datenbankmodell (ORM) implementieren
- [ ] Migrations-Workflow einrichten

### KI / Prognose
- [ ] KNN-Modell aufsetzen (Long/Short-Prognose)
- [ ] Trainingsdaten aufbereiten
- [ ] Modell trainieren und evaluieren
- [ ] Virtuelle Long- und Short-Trades zur Modellvalidierung

### Backend
- [ ] REST API für Kursabfragen (z.B. `/kurse?aktie=AAPL&von=...&bis=...`)
- [ ] Scheduler-Service für den 5-Minuten-Abruf (z.B. APScheduler oder Celery Beat)
- [ ] Datenquelle anbinden (API-Key-Verwaltung, Rate-Limit beachten)

### Frontend
- [ ] Dashboard mit Gewinn/Verlust-Übersicht
- [ ] Top 10 Long-Kandidaten anzeigen
- [ ] Top 10 Short-Kandidaten anzeigen
- [ ] Kursverläufe visualisieren

---

## Technologie-Stack (Vorschläge)

| Bereich       | Technologie                       |
|---------------|-----------------------------------|
| Backend       | Python / FastAPI                  |
| ML            | Scikit-learn, NumPy, Pandas       |
| Hintergrundjobs | Celery + Redis                  |
| Datenbank     | PostgreSQL + SQLAlchemy           |
| Frontend      | Vue.js + Chart.js                 |
| Deployment    | Docker / docker-compose           |

---

## Offene Fragen
- Welche Datenquelle soll genutzt werden? (z.B. Yahoo Finance, Alpha Vantage, Polygon.io)
- Welche Aktien / Märkte sollen abgedeckt werden? (Liste der Ticker pflegen)
- Soll `datum` und `uhrzeit` getrennt gespeichert werden oder als ein `DATETIME`/`TIMESTAMP`-Feld?
- Welche SQL-Datenbank? (SQLite für den Start, PostgreSQL für Produktion)
- Wie oft sollen Prognosen aktualisiert werden?
- Soll das System reine Simulation bleiben oder echte Orders ermöglichen?

---

## Nächste Schritte
- [ ] Datenquelle auswählen und API-Key beschaffen
- [ ] Ticker-Liste der gewünschten Aktien festlegen
- [ ] SQL-Datenbank und Schema einrichten (ggf. SQLite für Entwicklung)
- [ ] Scheduler mit erstem Abruf-Job implementieren
- [ ] Datenbankschreibung testen (Datum, Uhrzeit, Aktie, Wert)
- [ ] Technologie-Stack final entscheiden
- [ ] Projektstruktur (Verzeichnisse, Module) definieren
- [ ] Roadmap.md aus dieser Todo generieren
