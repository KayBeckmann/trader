from fastapi import FastAPI

app = FastAPI(title="Trader API")


@app.get("/health")
def health():
    return {"status": "ok"}
