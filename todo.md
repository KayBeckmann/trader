# Todo: KI-Aktien-Analyse

Dieses Dokument beschreibt die Schritte zur Entwicklung einer Anwendung für die Analyse und Vorhersage von Aktienkursen.

## Phase 1: Projekt-Setup & Basis-Architektur
- [x] **Technologiestack definieren:** Festlegen des Python-Frameworks (FastAPI), der Datenbank (PostgreSQL) und des Frontend-Frameworks (Vue.js 3).
- [x] **Projektstruktur initialisieren:** Erstellen der grundlegenden Ordnerstruktur und der Docker-Konfiguration.
- [x] **Backend-Architektur festlegen:** Aufteilung in drei Dienste (Data-Fetcher, KNN-Worker, API-Server) mit WebSocket-Kommunikation.
- [ ] **Datenquelle identifizieren:** Eine zuverlässige API für die Kursdaten des "MSCI World All Countries" Index finden.
- [x] **Datenbank-Schema entwerfen:** Die notwendigen SQL-Tabellen für Aktien, Kurse und Vorhersagen definieren.
- [x] **Docker-Compose-Setup erweitern:** Die `docker-compose.yml` für die drei Backend-Dienste, Frontend und DB anpassen.

## Phase 2: Backend-Services Implementierung

### Data-Fetcher Service
- [x] **Datenabruf implementieren:** Ein Skript entwickeln, das aktuelle und historische Kursdaten von der API abruft (aktuell simuliert).
- [x] **Scheduler integrieren:** Den Datenabruf so planen, dass er alle 5 Minuten ausgeführt wird.
- [x] **Datenbank-Anbindung:** Die abgerufenen Daten in der PostgreSQL-Datenbank speichern.
- [x] **Börsenzeiten & Crypto-Logik:** Implementiert, um nur zu Öffnungszeiten Aktien und rund um die Uhr Kryptos abzufragen.

### Trainer Service
- [x] **Redis-Integration:** Eine Redis-Instanz für die asynchrone Kommunikation einrichten.
    - [x] Der Data-Fetcher publiziert eine Nachricht nach erfolgreichem Datenabruf.
    - [x] Der Trainer lauscht auf diese Nachrichten, um die Analyse zu starten.
- [x] **Datenbank-Anbindung:** Die abgerufenen Daten aus der `stock_prices` Tabelle lesen.
- [x] **Virtuelle Positionen erstellen:** Für jeden Datensatz eine virtuelle Long- und Short-Position erstellen.
    - [x] Ordergebühr: 5€
    - [x] Ordergröße: 100€
- [x] **Daten in `training` Tabelle speichern:** Die erstellten Positionen mit Zeitstempel in der Datenbank speichern.

### KNN-Worker Service
- [x] **Redis-Integration:** Eine Redis-Instanz für die asynchrone Kommunikation zwischen dem Data-Fetcher und dem KNN-Worker einrichten.
    - [x] Der Data-Fetcher publiziert eine Nachricht nach erfolgreichem Datenabruf.
    - [x] Der KNN-Worker lauscht auf diese Nachrichten, um die Analyse zu starten.
- [x] **Handelszeiten-Logik:** Eine Funktion implementieren, die prüft, ob die globalen Börsen geöffnet sind.
- [x] **Grundgerüst des Neuronalen Netzes (Eigenentwicklung):** Das Modell von Grund auf mit Python/NumPy entwickeln.
- [x] **Datenvorverarbeitung:** Die Rohdaten aus der DB für das Training des Netzes normalisieren und aufbereiten.
- [x] **Vorhersage-Implementierung:** Die Logik erstellen, die basierend auf dem NN-Output die Top 10 Long- und Short-Positionen identifiziert.
- [ ] **Kommunikation mit API-Server:** Mechanismus implementieren, um neue Vorhersagen an den API-Server zu senden.
- [x] **Automatisches Training:** Den Backpropagation-Prozess implementieren, der nach 1 und 2 Stunden zur Neubewertung und zum Training des Modells angestoßen wird.
- [ ] **Performance-Tracking:** Die Logik zur Berechnung von Gewinn und Verlust für die Auswertung entwickeln.

### API-Server Service

### Trader Service
- [x] **Redis-Integration:** Auf Vorhersagen vom KNN-Worker lauschen.
- [x] **Virtuelle Orders erstellen:** Basierend auf den Vorhersagen Trades in der `trades` Tabelle öffnen.
- [x] **Gewinn/Verlust berechnen:** Offene Trades nach einer bestimmten Zeit schließen und den G/V berechnen.

- [ ] **REST-API Endpunkte definieren:**
    - [ ] Endpunkt für die initialen Top 10 Listen.
    - [ ] Endpunkt für die Gewinn/Verlust-Daten zur Visualisierung.
    - [ ] Endpunkt, der die Börsenöffnungszeiten übermittelt.
- [ ] **WebSocket-Implementierung:**
    - [ ] Einen WebSocket-Endpunkt einrichten, zu dem sich das Frontend verbinden kann.
    - [ ] Logik implementieren, um neue Vorhersagen vom KNN-Worker zu empfangen und an alle verbundenen Clients zu pushen.

## Phase 3: Web-Frontend
- [ ] **Webseite strukturieren:** Das grundlegende HTML/CSS-Layout erstellen.
- [ ] **WebSocket-Client implementieren:** Die Verbindung zum Backend herstellen und auf neue Daten lauschen.
- [ ] **Daten-Anzeige:** Die Top 10 Listen dynamisch auf der Webseite anzeigen und bei Push-Events aktualisieren.
- [ ] **Graphen-Visualisierung:** Den Gewinn/Verlust-Verlauf mit einer Charting-Bibliothek (z.B. Chart.js) visualisieren.
- [ ] **Zeitzonen-Umrechnung:** Die Börsenöffnungszeiten im Frontend in die lokale Zeitzone des Benutzers umrechnen und anzeigen.
- [ ] **Wiki-Sektion erstellen:** Einen Bereich für die Dokumentation der Anwendungsfunktionen und -architektur anlegen.

## Phase 4: Orchestrierung & Deployment
- [ ] **Haupt-Anwendung:** Ein zentrales Skript erstellen, das alle Prozesse (Datenabruf, Analyse, Training) steuert.
- [ ] **Dokumentation:** Die `README.md` mit allen notwendigen Anweisungen für Setup und Betrieb vervollständigen.
