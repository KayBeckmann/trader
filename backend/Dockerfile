FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./proj /app/proj

CMD ["uvicorn", "proj.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
