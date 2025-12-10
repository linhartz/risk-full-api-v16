# engine/hope_engine.py
from typing import Dict, Any, List
import math
import statistics

class HopeEngine:
    """Estimate Hope Mispricing Index (HMI) and aggregate sentiments."""

    @staticmethod
    def compute_hmi(market_expectation: float, objective_probability: float) -> Dict[str, Any]:
        if objective_probability is None or objective_probability <= 0:
            return {"hmi": None, "error": "objective_prob must be > 0", "hmi_normalized": 0.0}
        hmi = market_expectation / objective_probability
        # saturating transform to 0..1
        try:
            hmi_clipped = min(max(hmi, 0.0), 1e6)
            # transform with log and exp to compress large ratios
            norm = 1 - math.exp(-math.log10(hmi_clipped + 1))
            norm = max(0.0, min(1.0, norm))
        except Exception:
            norm = 0.0
        return {"hmi": hmi, "hmi_normalized": norm}

    @staticmethod
    def aggregate_sentiment_from_sources(sentiments: List[float]) -> Dict[str, Any]:
        if not sentiments:
            return {"mean": 0.0, "std": 0.0, "count": 0}
        mean = statistics.mean(sentiments)
        std = statistics.pstdev(sentiments) if len(sentiments) > 1 else 0.0
        return {"mean": round(mean, 6), "std": round(std, 6), "count": len(sentiments)}
