from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import KNNResult
from sqlalchemy import desc

router = APIRouter()

@router.get("/knn/top")
def get_top_knn_results(db: Session = Depends(get_db)):
    """
    Get the most recent KNN predictions.
    Returns the top 10 long and short predictions with their scores.
    """
    # Get the latest timestamp to identify the most recent prediction batch
    latest_timestamp_result = db.query(KNNResult.created_at).order_by(desc(KNNResult.created_at)).first()
    if not latest_timestamp_result:
        return {"long": [], "short": [], "message": "No predictions available yet. System needs time to collect data and train."}

    latest_timestamp = latest_timestamp_result[0]

    # Get all results from the latest batch (same timestamp)
    top_long = (
        db.query(KNNResult)
        .filter(
            KNNResult.type == "long",
            KNNResult.created_at == latest_timestamp
        )
        .order_by(KNNResult.rank)
        .limit(10)
        .all()
    )
    top_short = (
        db.query(KNNResult)
        .filter(
            KNNResult.type == "short",
            KNNResult.created_at == latest_timestamp
        )
        .order_by(KNNResult.rank)
        .limit(10)
        .all()
    )

    # Convert to dict with score included
    long_results = [{"id": r.id, "symbol": r.symbol, "rank": r.rank, "score": r.score} for r in top_long]
    short_results = [{"id": r.id, "symbol": r.symbol, "rank": r.rank, "score": r.score} for r in top_short]

    return {"long": long_results, "short": short_results}
