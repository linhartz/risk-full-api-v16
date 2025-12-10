# engine/hhi_engine.py
from typing import Dict, Any

class HHICalculator:
    """
    Compute Herfindahl–Hirschman Index (HHI)
    """

    def compute_hhi_structured(self, weights: Dict[str, float]) -> Dict[str, Any]:
        """
        weights = { "ISIN1": 40, "ISIN2": 30, ... }
        Values can be percentages or absolute weights — normalized automatically.
        """
        if not weights:
            return {"error": "No weights provided", "hhi": None}

        total = sum(weights.values())
        if total == 0:
            return {"error": "Total weights = 0", "hhi": None}

        items = []
        hhi = 0.0
        for isin, w in weights.items():
            pct = w / total
            pct2 = pct * pct
            hhi += pct2
            items.append({"isin": isin, "weight": w, "pct": round(pct, 6), "pct_sq": round(pct2, 6)})

        n = len(weights)
        # normalized HHI: remap from [1/n .. 1] to [0..1]
        hhi_normalized = (hhi - (1.0 / n)) / (1.0 - (1.0 / n)) if n > 1 else 1.0

        return {
            "hhi": round(hhi, 6),
            "hhi_normalized": round(hhi_normalized, 6),
            "n": n,
            "total_weight": total,
            "items": items,
        }

def compute_hhi_for_portfolio(isins, weights):
    """
    Wrapper used by /hhi/run.
    Accepts lists or comma-separated strings.
    """
    if isinstance(isins, str):
        isins = [i.strip() for i in isins.split(",") if i.strip()]
    if isinstance(weights, str):
        weights = [w.strip() for w in weights.split(",") if w.strip()]

    try:
        weights = [float(w) for w in weights]
    except Exception:
        return {"error": "Weights must be numeric"}

    if len(isins) != len(weights):
        return {"error": "ISINs count does not match weights count"}

    paired = {isins[i]: weights[i] for i in range(len(isins))}
    calc = HHICalculator()
    return calc.compute_hhi_structured(paired)
