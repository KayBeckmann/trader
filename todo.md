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

### Datenaufbereitung (Feature Engineering)
- [ ] Relativen Kurswert berechnen: aktueller Kurs im Verhältnis zum Vergangenheitswert
  - Kurs unverändert → `0`
  - Kurs gefallen → negativer Wert, max. `-1`
  - Kurs gestiegen → positiver Wert, max. `+1`
- [ ] Normalisierung auf den Bereich `[-1, 1]` via **Min-Max-Skalierung** über ein rollendes Zeitfenster
- [ ] Drei Zeitfenster pro Aktie berechnen:
  - `delta_5m` – Veränderung der letzten 5 Minuten
  - `delta_20m` – Veränderung der letzten 20 Minuten
  - `delta_60m` – Veränderung der letzten 60 Minuten
- [ ] Feature-Vektor pro Aktie: `[delta_5m, delta_20m, delta_60m]`
- [ ] Alle Aktien und alle Zeitfenster zu einem gemeinsamen Eingabe-Tensor zusammenführen

### KI / Prognose (KNN)
- [ ] KNN-Architektur definieren:
  - **Eingabe:** Alle Aktien × 3 Zeitfenster (flacher oder strukturierter Eingabe-Vektor)
  - **Ausgabe:** Ein Wert je Aktie im Bereich `[-1, 1]`
    - `-1` → Short-Signal
    - ` 0` → Keine Aktion
    - `+1` → Long-Signal
- [ ] Alle Aktien werden **parallel** durch dasselbe Netz verarbeitet (kein sequenzieller Loop)
- [ ] Aktivierungsfunktion am Ausgang: `tanh` (liefert nativ `[-1, 1]`)
- [ ] KNN trifft **keine** automatischen Handelsentscheidungen
- [ ] Ausgabewerte werden nach Stärke sortiert und als Empfehlungsliste weitergereicht:
  - Top 10 Long-Kandidaten (höchste positive Werte, nahe `+1`)
  - Top 10 Short-Kandidaten (stärkste negative Werte, nahe `-1`)
- [ ] Modell trainieren und evaluieren

### Virtuelles Trading & Reinforcement Learning
- [ ] Jede KNN-Empfehlung wird automatisch als virtueller Trade ausgeführt
- [ ] Handelsgebühren realistisch erfassen:
  - Eröffnung: **0,5%** auf den Einsatz (wird sofort vom Kapital abgezogen)
  - Schließung: **0,5%** auf den aktuellen Positionswert zum Schlusszeitpunkt
  - Gesamtgebühr variiert je nach Kursentwicklung (nicht fix 1%)
  - Gebühren mindern das Ergebnis – Stop-Loss und Take-Profit beziehen sich auf den Nettoertrag nach Gebühren
- [ ] Virtuelles Kapital pro Trade: **100 €**
- [ ] Stop-Loss bei **-15%** (inkl. Gebühren) → Trade wird automatisch geschlossen
- [ ] Take-Profit bei **+15%** (inkl. Gebühren) → Trade wird automatisch geschlossen
- [ ] Maximale Haltedauer: **1 Stunde** – danach wird der Trade zwangsweise geschlossen
- [ ] Ergebnis-Auswertung nach Trade-Schließung (absolut in €):
  - Take-Profit ausgelöst → **maximale positive Bestärkung** (`reward = +1`)
  - Stop-Loss ausgelöst → **maximale negative Bestärkung** (`reward = -1`)
  - Timeout mit `|ergebnis| < 10 €` → **`reward = null`**, wird ignoriert
  - Timeout mit Gewinn ≥ 10 € → positive Bestärkung (proportional zum Ergebnis)
  - Timeout mit Verlust ≥ 10 € → negative Bestärkung (proportional zum Ergebnis)
- [ ] Reward-Signal wird ans KNN zurückgegeben (Reinforcement Learning)
- [ ] Tabelle `trades` in der Datenbank definieren:
  - `id` – Primärschlüssel
  - `aktie` – Tickersymbol
  - `richtung` – `long` oder `short`
  - `eroeffnet_at` – Zeitpunkt der Eröffnung
  - `geschlossen_at` – Zeitpunkt der Schließung
  - `schliessgrund` – `stop_loss`, `take_profit` oder `timeout`
  - `einsatz_eur` – virtueller Einsatz (100 €)
  - `gebuehr_eroeffnung_eur` – Gebühr beim Eröffnen (0,5% auf Einsatz)
  - `gebuehr_schliessung_eur` – Gebühr beim Schließen (0,5% auf Positionswert)
  - `ergebnis_eur` – absolutes Ergebnis in € nach Gebühren
  - `reward` – Reward-Signal (`-1` bis `+1`, oder `null` wenn ignoriert)
- [ ] Tabelle `statistik` oder aggregierte View je Aktie:
  - Anzahl Trades gesamt
  - Anzahl Gewinntrades / Verlusttrades
  - Gesamtgewinn / Gesamtverlust in €
  - Trefferquote in %
  - Durchschnittliches Ergebnis pro Trade

### Backend
- [ ] REST API für Kursabfragen (z.B. `/kurse?aktie=AAPL&von=...&bis=...`)
- [ ] Scheduler-Service für den 5-Minuten-Abruf (z.B. APScheduler oder Celery Beat)
- [ ] Datenquelle anbinden (API-Key-Verwaltung, Rate-Limit beachten)

### Frontend
- [ ] Dashboard als Hauptansicht
- [ ] Top 10 Long-Kandidaten mit KNN-Ausgabewert als Gewichtungsindikator (Balken/Farbskala)
- [ ] Top 10 Short-Kandidaten mit KNN-Ausgabewert als Gewichtungsindikator (Balken/Farbskala)
- [ ] Je Aktie in der Top-10-Liste: Gewinn/Verlust-Statistik anzeigen:
  - Trefferquote (% Gewinntrades)
  - Gesamtergebnis in € (kumuliert)
  - Anzahl Trades
- [ ] Gesamtstatistik des KNN über alle Aktien (Portfolio-Sicht)
- [ ] Nutzer entscheidet selbst, ob und wie er handelt (kein automatischer Handel)
- [ ] Kursverläufe der empfohlenen Aktien visualisieren

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
- Welche Aktien / Märkte sollen abgedeckt werden? (Ticker-Liste festlegen)
- Soll `timestamp` als ein Feld gespeichert werden oder getrennt als `datum` + `uhrzeit`?
- Welche SQL-Datenbank? (SQLite für Entwicklung, PostgreSQL für Produktion)
- Wie groß soll das rollende Fenster für die Min-Max-Normalisierung sein? (z.B. 24h, 7 Tage)

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
