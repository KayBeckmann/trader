# Todo: KI-Aktien-Analyse

Dieses Dokument beschreibt die Schritte zur Entwicklung einer Anwendung für die Analyse und Vorhersage von Aktienkursen.

## Phase 1: Projekt-Setup & Datenbeschaffung
- [x] **Technologiestack definieren:** Festlegen des Python-Frameworks (FastAPI), der Datenbank (PostgreSQL) und des Frontend-Frameworks (Vue.js 3).
- [x] **Projektstruktur initialisieren:** Erstellen der grundlegenden Ordnerstruktur und der Docker-Konfiguration.
- [ ] **Datenquelle identifizieren:** Eine zuverlässige API für die Kursdaten des "MSCI World All Countries" Index finden.
- [ ] **Datenabruf implementieren:** Ein Skript entwickeln, das aktuelle und historische Kursdaten von der API abruft.
- [ ] **Datenbank-Schema entwerfen:** Die notwendigen SQL-Tabellen für Aktien, Kurse und Vorhersagen definieren.
- [ ] **Datenbank-Integration:** Einrichten der Datenbank und Schreiben der Logik zum Speichern der abgerufenen Daten.

## Phase 2: Kernlogik & Neuronales Netz
- [ ] **Handelszeiten-Logik:** Eine Funktion implementieren, die prüft, ob die globalen Börsen geöffnet sind.
- [ ] **Grundgerüst des Neuronalen Netzes (Eigenentwicklung):** Das Modell von Grund auf mit Python/NumPy entwickeln.
- [ ] **Datenvorverarbeitung:** Die Rohdaten für das Training des Netzes normalisieren und aufbereiten.
- [ ] **Vorhersage-Implementierung:** Die Logik erstellen, die basierend auf dem NN-Output die Top 10 Long- und Short-Positionen identifiziert.
- [ ] **Automatisches Training:** Den Backpropagation-Prozess implementieren, der nach 1 und 2 Stunden zur Neubewertung und zum Training des Modells angestoßen wird.
- [ ] **Performance-Tracking:** Die Logik zur Berechnung von Gewinn und Verlust für die Auswertung entwickeln.

## Phase 3: Web-Backend (API)
- [ ] **API-Endpunkte definieren:**
    - [ ] Ein Endpunkt, der die Top 10 Listen bereitstellt.
    - [ ] Ein Endpunkt für die Gewinn/Verlust-Daten zur Visualisierung.
    - [ ] Ein Endpunkt, der die Börsenöffnungszeiten übermittelt.

## Phase 4: Web-Frontend
- [ ] **Webseite strukturieren:** Das grundlegende HTML/CSS-Layout erstellen.
- [ ] **Daten-Anzeige:** Die Top 10 Listen dynamisch auf der Webseite anzeigen.
- [ ] **Graphen-Visualisierung:** Den Gewinn/Verlust-Verlauf mit einer Charting-Bibliothek (z.B. Chart.js) visualisieren.
- [ ] **Zeitzonen-Umrechnung:** Die Börsenöffnungszeiten im Frontend in die lokale Zeitzone des Benutzers umrechnen und anzeigen.
- [ ] **Wiki-Sektion erstellen:** Einen Bereich für die Dokumentation der Anwendungsfunktionen und -architektur anlegen.

## Phase 5: Orchestrierung & Deployment
- [ ] **Haupt-Anwendung:** Ein zentrales Skript erstellen, das alle Prozesse (Datenabruf, Analyse, Training) steuert.
- [ ] **Scheduler einrichten:** Den Prozess so planen, dass er automatisch nur während der Handelszeiten läuft.
- [ ] **Dokumentation:** Die `README.md` mit allen notwendigen Anweisungen für Setup und Betrieb vervollständigen.
