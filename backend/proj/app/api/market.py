"""
Market-related API endpoints.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/market-hours")
def get_market_hours():
    """
    Returns the stock market opening hours in UTC.

    US Stock Market (NYSE/NASDAQ):
    - Regular trading: 14:30 - 21:00 UTC (9:30 AM - 4:00 PM ET)
    - Pre-market: 09:00 - 14:30 UTC (4:00 AM - 9:30 AM ET)
    - After-hours: 21:00 - 01:00 UTC (4:00 PM - 8:00 PM ET)

    Note: Hours may vary due to daylight saving time.
    """
    return {
        "timezone": "UTC",
        "markets": {
            "us_stock": {
                "name": "US Stock Market (NYSE/NASDAQ)",
                "regular_hours": {
                    "open": "14:30",
                    "close": "21:00"
                },
                "pre_market": {
                    "open": "09:00",
                    "close": "14:30"
                },
                "after_hours": {
                    "open": "21:00",
                    "close": "01:00"
                },
                "trading_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "note": "Times are in UTC. Adjust for daylight saving time."
            },
            "crypto": {
                "name": "Cryptocurrency Markets",
                "regular_hours": {
                    "open": "00:00",
                    "close": "23:59"
                },
                "trading_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "note": "Crypto markets are open 24/7"
            }
        }
    }
