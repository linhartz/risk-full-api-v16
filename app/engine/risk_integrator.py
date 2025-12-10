# engine/risk_integrator.py
from typing import Dict, Any, List
from engine.hhi_engine import HHICalculator
from engine.hope_engine import HopeEngine
from engine.chaotic_risk import ChaoticRisk  # NEW

class RiskIntegrator:
    def __init__(self, config: Dict[str, Any] = None):
        self.hhi = HHICalculator()
        self.hope = HopeEngine()
        self.cr = ChaoticRisk(config=config.get("chaotic", {}) if config else None)

    def integrate(
        self,
        portfolio: List[Dict[str, Any]],
        nur: Dict[str, Any],
        rsz: Dict[str, Any],
        cycles: Dict[str, Any],
        market_expectation: float = None,
        objective_prob: float = None,
        sentiments: List[float] = None,
        provocations: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # 1) HHI
        weights = {p["isin"]: p.get("weight", 0.0) for p in portfolio}
        hhi_struct = self.hhi.compute_hhi_structured(weights)

        # 2) HOPE
        if market_expectation is not None and objective_prob is not None:
            hope_res = self.hope.compute_hmi(market_expectation, objective_prob)
        else:
            hope_res = {"hmi": None, "hmi_normalized": 0.0}
        hope_norm = hope_res.get("hmi_normalized", 0.0) or 0.0

        # 3) sentiments
        sentiment_agg = self.hope.aggregate_sentiment_from_sources(sentiments or [])

        # 4) normalize incoming signals
        nur_score = (nur.get("severity_score", 0.0) if isinstance(nur, dict) else 0.0)
        rsz_score = (rsz.get("action_weight", 0.0) if isinstance(rsz, dict) else 0.0)
        cycles_score = (cycles.get("cycle_pressure", 0.0) if isinstance(cycles, dict) else 0.0)

        # 5) Chaotic Risk layer (new)
        cr_res = self.cr.compute_from_provocations(provocations or [], nur=nur, rsz=rsz)
        cr_scalar = cr_res.get("cr_scalar", 0.0) or 0.0

        # 6) composite weighting (adjusted to include CR)
        composite = (
            0.20 * hhi_struct.get("hhi_normalized", 0.0) +  # slightly reduced
            0.15 * nur_score +
            0.10 * rsz_score +
            0.15 * cycles_score +
            0.20 * hope_norm +
            0.20 * cr_scalar
        )

        # thresholds can be tuned
        if composite > 0.65:
            risk_level = "DANGER"
        elif composite > 0.4:
            risk_level = "ELEVATED"
        elif composite > 0.2:
            risk_level = "WATCH"
        else:
            risk_level = "STABLE"

        return {
            "portfolio_hhi": hhi_struct,
            "hope": hope_res,
            "sentiment_agg": sentiment_agg,
            "nur": nur,
            "rsz": rsz,
            "cycles": cycles,
            "provocations": provocations or [],
            "chaotic_risk": cr_res,
            "composite": round(composite, 6),
            "risk_level": risk_level,
        }

# global instance for easy import by FastAPI
risk_integrator = RiskIntegrator()
