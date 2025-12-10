# engine/chaotic_risk.py
from typing import List, Dict, Any
import math
import statistics

"""
Chaotic Risk Layer (CR)
- vstup: seznam "provocation" signálů (institucionální / individuální)
  každý signál: { "id": str, "source_type": "institutional"|"individual"|..., "intensity": float, "vector": str, "timestamp": ..., "confidence": float (0..1) }
- dále přijímá NUR a RSZ struktury (slouží k modulaci)
- výstup: dict { "cr_scalar": 0..1, "components": {...}, "flags": [...] }
"""

def _norm01(x: float) -> float:
    """Sigmoid-like squash to 0..1 but smoother for negatives."""
    try:
        return max(0.0, min(1.0, x))
    except Exception:
        return 0.0

def _entropy_of_weights(weights: List[float]) -> float:
    """Normalized entropy (0..1). If single dominant source -> low entropy (near 0)."""
    if not weights:
        return 0.0
    s = sum(weights)
    if s <= 0:
        return 0.0
    ps = [w / s for w in weights if w > 0]
    if not ps:
        return 0.0
    ent = -sum(p * math.log(p + 1e-12) for p in ps)
    # normalize by log(N)
    max_ent = math.log(len(ps))
    return ent / max_ent if max_ent > 0 else 0.0

class ChaoticRisk:
    def __init__(self, config: Dict[str, Any] = None):
        # Configurable weights
        cfg = config or {}
        self.w_institutional = cfg.get("w_institutional", 1.5)  # institutional provokes stronger
        self.w_individual = cfg.get("w_individual", 1.0)
        self.w_vector_coherence = cfg.get("w_vector_coherence", 1.0)
        self.w_confidence = cfg.get("w_confidence", 1.0)
        self.global_dampen = cfg.get("global_dampen", 0.9)  # general dampening to avoid overreaction

    def compute_from_provocations(
        self,
        provocations: List[Dict[str, Any]],
        nur: Dict[str, Any] = None,
        rsz: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        # defensive
        provocations = provocations or []
        nur = nur or {}
        rsz = rsz or {}

        if not provocations:
            return {"cr_scalar": 0.0, "components": {}, "flags": []}

        # gather weighted intensities, grouped by source_type and vector
        inst_vals = []
        ind_vals = []
        vector_map = {}
        confidences = []

        for p in provocations:
            intensity = float(p.get("intensity", 0.0) or 0.0)
            src = (p.get("source_type") or "individual").lower()
            conf = float(p.get("confidence", 0.0) or 0.0)
            vect = p.get("vector") or "unknown"

            weight = 1.0
            if src in ("institutional", "state", "agency"):
                weight = self.w_institutional
            else:
                weight = self.w_individual

            weighted = intensity * weight
            if src in ("institutional", "state", "agency"):
                inst_vals.append(weighted)
            else:
                ind_vals.append(weighted)

            vector_map.setdefault(vect, 0.0)
            vector_map[vect] += abs(weighted)

            confidences.append(conf)

        sum_inst = sum(inst_vals)
        sum_ind = sum(ind_vals)
        total_energy = sum_inst + sum_ind + 1e-12

        # vector coherence: if energy concentrated into few vectors -> high coherence (can amplify)
        vector_weights = list(vector_map.values())
        entropy = _entropy_of_weights(vector_weights)  # 0..1 (0 dominated, 1 diffuse)
        coherence = 1.0 - entropy  # 0..1 (higher = more coherent / focused attack)

        # average confidence
        avg_conf = statistics.mean(confidences) if confidences else 0.0

        # base raw score (unbounded)
        raw = (sum_inst + sum_ind) * (1.0 + self.w_vector_coherence * coherence) * (1.0 + self.w_confidence * avg_conf)

        # modulation by NUR (novelty) and RSZ (stability)
        # if NUR indicates high novelty/severity, amplify; if RSZ suggests stability, dampen
        nur_severity = 0.0
        try:
            nur_severity = float(nur.get("severity_score", nur.get("severity", 0.0) or 0.0))
        except Exception:
            nur_severity = 0.0

        rsz_stability = 0.0
        try:
            # rsz.action_weight or cycle-like stability indicator
            rsz_stability = float(rsz.get("stability_score", rsz.get("action_weight", 0.0) or 0.0))
        except Exception:
            rsz_stability = 0.0

        # Amplify with novelty, but dampen with stability (conceptual)
        # Map nur_severity to amplifier in 0..2
        nur_amp = 1.0 + _norm01(nur_severity)  # if severity 0..1 -> 1..2
        # Map rsz_stability to dampener 0.5..1.2 (more stability -> smaller)
        rsz_damp = 1.2 - (_norm01(rsz_stability) * 0.7)

        modulated = raw * nur_amp * rsz_damp

        # Normalization strategy:
        # Want cr_scalar in 0..1. Use arctan/log-based compression to respect heavy tails.
        try:
            # scale by a heuristic factor based on total_energy to keep units consistent
            scale = 1.0 + math.log10(total_energy + 1.0)
            compressed = math.atan(modulated / (scale + 1e-6)) / (math.pi / 2)  # maps to 0..1
        except Exception:
            compressed = 0.0

        # apply global dampen
        cr_scalar = _norm01(compressed * self.global_dampen)

        components = {
            "sum_institutional": round(sum_inst, 6),
            "sum_individual": round(sum_ind, 6),
            "total_energy": round(total_energy, 6),
            "vector_count": len(vector_map),
            "vector_coherence": round(coherence, 6),
            "avg_confidence": round(avg_conf, 6),
            "nur_amp": round(nur_amp, 6),
            "rsz_damp": round(rsz_damp, 6),
            "raw_modulated": round(modulated, 6),
            "compressed": round(compressed, 6)
        }

        flags = []
        # heuristics flags
        if coherence > 0.8 and total_energy > 10.0:
            flags.append("FOCUSED_HIGH_INTENSITY")
        if sum_inst > (0.6 * total_energy) and total_energy > 1.0:
            flags.append("INSTITUTIONAL_DOMINANCE")
        if avg_conf < 0.25 and total_energy > 2.0:
            flags.append("LOW_CONFIDENCE_NOISE")

        return {
            "cr_scalar": round(cr_scalar, 6),
            "components": components,
            "flags": flags
        }
