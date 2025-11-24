from fastapi import FastAPI

app = FastAPI(title="Trader API")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Trader API"}
