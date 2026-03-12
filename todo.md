# Trader – Todo & Projektideen

## Projektziel
Ein modulares System, das Aktienkurse analysiert, per KI Prognosen erstellt und Ergebnisse übersichtlich darstellt.

---

## Kernfunktionen

### Datenbeschaffung
- [ ] Aktienkurse automatisch abrufen (z.B. via API)
- [ ] Historische Kursdaten laden und speichern
- [ ] Datenbankanbindung für persistente Speicherung

### KI / Prognose
- [ ] KNN-Modell aufsetzen (Long/Short-Prognose)
- [ ] Trainingsdaten aufbereiten
- [ ] Modell trainieren und evaluieren
- [ ] Virtuelle Long- und Short-Trades zur Modellvalidierung

### Backend
- [ ] REST API für Datenabfragen
- [ ] Hintergrundjobs für regelmäßige Datenaktualisierung
- [ ] Datenbankmodelle definieren

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
- Welche Datenquellen sollen genutzt werden? (z.B. Yahoo Finance, Alpha Vantage, eigene Daten)
- Welche Aktien / Märkte sollen abgedeckt werden?
- Wie oft sollen Prognosen aktualisiert werden?
- Soll das System reine Simulation bleiben oder echte Orders ermöglichen?

---

## Nächste Schritte
- [ ] Technologie-Stack final entscheiden
- [ ] Projektstruktur (Verzeichnisse, Module) definieren
- [ ] Erste Datenquelle anbinden und testen
- [ ] Roadmap.md aus dieser Todo generieren
