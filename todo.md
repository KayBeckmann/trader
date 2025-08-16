# Todo: KI-Aktien-Analyse

Dieses Dokument beschreibt die Schritte zur Entwicklung einer Anwendung für die Analyse und Vorhersage von Aktienkursen.

## Phase 1: Projekt-Setup & Basis-Architektur
- [x] **Technologiestack definieren:** Festlegen des Python-Frameworks (FastAPI), der Datenbank (PostgreSQL) und des Frontend-Frameworks (Vue.js 3).
- [x] **Projektstruktur initialisieren:** Erstellen der grundlegenden Ordnerstruktur und der Docker-Konfiguration.
- [x] **Backend-Architektur festlegen:** Aufteilung in drei Dienste (Data-Fetcher, KNN-Worker, API-Server) mit WebSocket-Kommunikation.
- [x] **Datenquelle identifizieren:** Eine zuverlässige API für die Kursdaten des "MSCI World All Countries" Index finden.
- [x] **Datenbank-Schema entwerfen:** Die notwendigen SQL-Tabellen für Aktien, Kurse und Vorhersagen definieren.
- [x] **Docker-Compose-Setup erweitern:** Die `docker-compose.yml` für die drei Backend-Dienste, Frontend und DB anpassen.

## Phase 2: Backend-Services Implementierung

### Data-Fetcher Service
- [x] **Datenabruf implementieren:** Ein Skript entwickeln, das aktuelle und historische Kursdaten von der API abruft (aktuell simuliert).
- [x] **Scheduler integrieren:** Den Datenabruf so planen, dass er alle 5 Minuten ausgeführt wird.
- [x] **Datenbank-Anbindung:** Die abgerufenen Daten in der PostgreSQL-Datenbank speichern.
- [x] **Börsenzeiten & Crypto-Logik:** Implementiert, um nur zu Öffnungszeiten Aktien und rund um die Uhr Kryptos abzufragen.

### Trainer Service
- [x] **Redis-Integration:** Lauscht auf Nachrichten vom Data-Fetcher.
- [x] **Virtuelle Positionen erstellen:** Erstellt für jeden neuen Datensatz virtuelle Long- und Short-Positionen zum Trainieren.
- [x] **Positions-Management:** Schließt Positionen bei 10% Stop-Loss/Take-Profit oder nach 1 Stunde.

### KNN-Worker Service
- [x] **Reinforcement Learning:** Trainiert das neuronale Netz basierend auf den Ergebnissen der geschlossenen Trades aus dem Trainer-Service.
    - [x] Positives Training bei Gewinn (>2%), negatives bei Verlust (<-2%), neutrales bei +/- 2%.
- [x] **Vorhersage-Implementierung:** Sagt die Top 10 Long- und Short-Aktien basierend auf dem trainierten Modell voraus.
- [x] **Redis-Integration:** Veröffentlicht die Top-10-Listen auf Redis für den Trader-Service.

### API-Server Service

### Trader Service
- [x] **Redis-Integration:** Lauscht auf die Top-10-Vorhersagen vom KNN-Worker.
- [x] **Live-Trading (virtuell):** Eröffnet Trades basierend auf den Vorhersagen.
- [x] **Positions-Management:** Schließt Positionen bei 10% Stop-Loss/Take-Profit oder nach 1 Stunde und speichert das Ergebnis.

- [x] **REST-API Endpunkte definieren:**
    - [x] Endpunkt für die initialen Top 10 Listen.
    - [x] Endpunkt für die Gewinn/Verlust-Daten zur Visualisierung.
    - [x] Endpunkt, der die Börsenöffnungszeiten übermittelt.
- [x] **WebSocket-Implementierung:**
    - [x] Einen WebSocket-Endpunkt einrichten, zu dem sich das Frontend verbinden kann.
    - [x] Logik implementieren, um neue Vorhersagen vom KNN-Worker zu empfangen und an alle verbundenen Clients zu pushen.

## Phase 3: Web-Frontend
- [x] **Webseite strukturieren:** Das grundlegende HTML/CSS-Layout erstellen.
- [x] **WebSocket-Client implementieren:** Die Verbindung zum Backend herstellen und auf neue Daten lauschen.
- [x] **Daten-Anzeige:** Die Top 10 Listen dynamisch auf der Webseite anzeigen und bei Push-Events aktualisieren.
- [x] **Graphen-Visualisierung:** Den Gewinn/Verlust-Verlauf mit einer Charting-Bibliothek (z.B. Chart.js) visualisieren.
- [ ] **Zeitzonen-Umrechnung:** Die Börsenöffnungszeiten im Frontend in die lokale Zeitzone des Benutzers umrechnen und anzeigen.
- [ ] **Wiki-Sektion erstellen:** Einen Bereich für die Dokumentation der Anwendungsfunktionen und -architektur anlegen.

## Phase 4: Orchestrierung & Deployment
- [ ] **Haupt-Anwendung:** Ein zentrales Skript erstellen, das alle Prozesse (Datenabruf, Analyse, Training) steuert.
- [ ] **Dokumentation:** Die `README.md` mit allen notwendigen Anweisungen für Setup und Betrieb vervollständigen.
