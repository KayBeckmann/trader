from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import KNNResult
from sqlalchemy import desc
from datetime import timedelta

router = APIRouter()

@router.get("/knn/top")
def get_top_knn_results(db: Session = Depends(get_db)):
    latest_timestamp_result = db.query(KNNResult.created_at).order_by(desc(KNNResult.created_at)).first()
    if not latest_timestamp_result:
        return {"long": [], "short": []}

    latest_timestamp = latest_timestamp_result[0]

    time_threshold = latest_timestamp - timedelta(seconds=5)

    top_long = (
        db.query(KNNResult)
        .filter(
            KNNResult.type == "long",
            KNNResult.created_at >= time_threshold
        )
        .order_by(desc(KNNResult.created_at), KNNResult.rank)
        .limit(10)
        .all()
    )
    top_short = (
        db.query(KNNResult)
        .filter(
            KNNResult.type == "short",
            KNNResult.created_at >= time_threshold
        )
        .order_by(desc(KNNResult.created_at), KNNResult.rank)
        .limit(10)
        .all()
    )
    return {"long": top_long, "short": top_short}
