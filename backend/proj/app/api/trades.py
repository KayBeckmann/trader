from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Trade

router = APIRouter()

@router.get("/trades")
def get_trades(db: Session = Depends(get_db)):
    return db.query(Trade).filter(Trade.status == "closed").all()
