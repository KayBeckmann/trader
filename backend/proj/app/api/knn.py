from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import KNNResult
from sqlalchemy import desc

router = APIRouter()

@router.get("/knn/top")
def get_top_knn_results(db: Session = Depends(get_db)):
    latest_timestamp = db.query(KNNResult.created_at).order_by(desc(KNNResult.created_at)).first()
    if not latest_timestamp:
        return {"long": [], "short": []}

    latest_timestamp = latest_timestamp[0]

    top_long = (
        db.query(KNNResult)
        .filter(KNNResult.type == "long", KNNResult.created_at == latest_timestamp)
        .order_by(KNNResult.rank)
        .limit(10)
        .all()
    )
    top_short = (
        db.query(KNNResult)
        .filter(KNNResult.type == "short", KNNResult.created_at == latest_timestamp)
        .order_by(KNNResult.rank)
        .limit(10)
        .all()
    )
    return {"long": top_long, "short": top_short}
