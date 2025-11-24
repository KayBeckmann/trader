# Ideen für ein modulares System

- Aktienwerte abrufen
- Werte in eine Datenbank speichern
- Werte aller Aktien gleichzeitig an ein KNN übergeben
- Long und Short Prognose durch das KNN
- Virtuelle Long- und Short-Trades, um das KNN trainieren zu können
- Webseite mit Gewinn/Verlust durch die Vorhersagen des KNN und Top 10 Long und Top 10 Short

## Vorgeschlagener Technologie-Stack

**Backend: Python**
- **Web-Framework:** FastAPI
- **Machine Learning:** Scikit-learn, NumPy, Pandas
- **Modulare Services:** Celery mit Redis
- **Datenbank:** PostgreSQL mit SQLAlchemy

**Frontend: Vue.js**
- **Framework:** Vue.js
- **Visualisierung:** Chart.js