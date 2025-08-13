# Microservices (Getrennte Container)
Hier teilst du dein Backend in logische, unabhängige Dienste auf, von denen jeder in seinem eigenen Docker-Container läuft. Dies ist der Ansatz, den du mit deiner Frage ansprichst.

Eine typische Aufteilung wäre:
1. API-Service (Container 1): Ein schlanker Webserver (z.B. mit FastAPI oder Flask), der nur Anfragen vom Frontend entgegennimmt, validiert und an andere Dienste weiterleitet.
2. Fetcher-Service (Container 2): Ein Dienst, der ausschließlich für die Beschaffung von Daten zuständig ist. Er könnte auf Befehl des API-Services oder zeitgesteuert laufen.
3. Processor-Service (Container 3): Dieser Dienst nimmt die beschafften Daten entgegen und führt die rechenintensiven Verarbeitungen durch.

Die Kommunikation zwischen diesen Containern erfolgt nicht mehr über direkte Funktionsaufrufe, sondern über das Netzwerk. Hierfür gibt es zwei gängige Muster:
- Synchrone Kommunikation (Direkte API-Aufrufe): Der API-Service ruft per HTTP direkt den Fetcher-Service auf und wartet auf eine Antwort. Eher unüblich für langlaufende Aufgaben.
- Asynchrone Kommunikation (Message Queue): Dies ist der robusteste und am häufigsten empfohlene Weg.

## Wie funktioniert die asynchrone Kommunikation?
Du fügst eine weitere Komponente hinzu: einen Message Broker (z.B. RabbitMQ oder Redis), der ebenfalls in einem eigenen Container läuft.

Der Prozess sieht dann so aus:
1. Das Frontend sendet eine Anfrage an den API-Service.
2. Der API-Service erstellt einen "Job" (eine Nachricht) und legt diesen in eine Warteschlange (Queue) im Message Broker. z.B. fetch-queue. Danach sendet er sofort eine Antwort an das Frontend ("Auftrag angenommen").
3. Der Fetcher-Service "hört" auf die fetch-queue. Sobald eine Nachricht da ist, nimmt er sie sich, beschafft die Daten und legt nach getaner Arbeit eine neue Nachricht in die process-queue.
4. Der Processor-Service "hört" auf die process-queue, nimmt sich die Nachricht, verarbeitet die Daten und speichert das Ergebnis in der Datenbank.
