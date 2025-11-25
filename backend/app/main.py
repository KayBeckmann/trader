from fastapi import FastAPI
from .database import engine
from . import models
from .api import knn, trades

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Trader API")

app.include_router(knn.router, prefix="/api")
app.include_router(trades.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Trader API"}
