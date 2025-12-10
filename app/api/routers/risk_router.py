from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from api.engine.risk_integrator import risk_integrator
from api.engine.hhi_engine import compute_hhi_for_portfolio
from api.engine.hope_engine import HopeEngine

router = APIRouter()

# -------------------------
# INPUT MODELS
# -------------------------
class PortfolioItem(BaseModel):
    isin: str
    weight: float

class RiskRequest(BaseModel):
    portfolio: List[PortfolioItem]
    nur: Dict[str, Any]
    rsz: Dict[str, Any]
    cycles: Dict[str, Any]
    market_expectation: Optional[float] = None
    objective_prob: Optional[float] = None
    sentiments: Optional[List[float]] = []
    provocations: Optional[List[Dict[str, Any]]] = []

# -------------------------
# ROUTES
# -------------------------
@router.post("/full")
def run_full_risk(req: RiskRequest):
    return risk_integrator.integrate(
        portfolio=[p.dict() for p in req.portfolio],
        nur=req.nur,
        rsz=req.rsz,
        cycles=req.cycles,
        market_expectation=req.market_expectation,
        objective_prob=req.objective_prob,
        sentiments=req.sentiments,
        provocations=req.provocations
    )

@router.post("/hhi")
def hhi_run(isins: str, weights: str):
    """
    Example:
    /risk/hhi?isins=US111,US222&weights=40,60
    """
    return compute_hhi_for_portfolio(isins, weights)

@router.post("/sentiment")
def sentiment_aggregate(values: List[float]):
    return HopeEngine.aggregate_sentiment_from_sources(values)
