"""
ThreatEngine — multi-factor threat scoring and target prioritization.

Score = BaseScore × ConfWeight × ProximityWeight × OperatorWeight × MissionWeight
All weights are clamped to [0, 10].
"""
from typing import List, Dict, Optional
from app.core.config import settings, MISSION_MULTIPLIERS


# Base scores per military class
_BASE_SCORES: Dict[str, float] = {
    "missile_launcher": 10.0,
    "sam_system":        9.5,
    "radar_array":       9.0,
    "c2_node":           8.5,
    "fighter_aircraft":  8.5,
    "command_vehicle":   8.0,
    "warship":           7.5,
    "armored_vehicle":   6.5,
    "helicopter":        6.5,
    "ammo_cache":        5.5,
    "comms_kit":         5.0,
    "scout_vehicle":     4.0,
    "field_equipment":   3.0,
    "supply_truck":      3.5,
    "infantry":          2.5,
    "personnel":         1.5,
    "unidentified_asset":4.0,
    "default":           4.0,
}

_ACTIONS: Dict[str, str] = {
    "missile_launcher":  "IMMEDIATE STRIKE — Time-critical target",
    "sam_system":        "SEAD TASKING — Suppress before strike package",
    "radar_array":       "PRIORITY STRIKE — Degrade C2 network",
    "c2_node":           "PRIORITY STRIKE — Disrupt command chain",
    "fighter_aircraft":  "AIR INTERCEPT — Coordinate CAP",
    "command_vehicle":   "HIGH PRIORITY — Sever adversary coordination",
    "warship":           "MARITIME STRIKE — Coordinate naval assets",
    "armored_vehicle":   "ANTI-ARMOR TASKING — Brigade coordination",
    "default":           "CONTINUE ISR — Monitor and track",
}

def _priority_label(score: float) -> str:
    if score >= 9.0: return "🔴 P1 — STRIKE"
    if score >= 7.5: return "🟠 P2 — HIGH"
    if score >= 5.5: return "🟡 P3 — MEDIUM"
    return  "🟢 P4 — MONITOR"

def _conf_weight(conf: float) -> float:
    """Quadratic: high-confidence detections count more."""
    return round(0.60 + 0.40 * (conf ** 1.5), 4)

def _proximity_weight(asset: dict, all_assets: List[dict]) -> float:
    """Assets near other high-value targets receive a proximity bonus."""
    if asset.get("lat") is None:
        return 1.0
    nearby = sum(
        1 for other in all_assets
        if other.get("asset_id") != asset.get("asset_id")
        and other.get("lat") is not None
        and (
            (asset["lat"] - other["lat"])**2 +
            (asset["lon"] - other["lon"])**2
        ) ** 0.5 < 0.008        # ~0.8 km at mid-latitudes
        and other.get("threat_score", 0) >= 6.0
    )
    return min(1.0 + 0.04 * nearby, 1.25)


def prioritize(
    assets: List[dict],
    operator_overrides: Optional[Dict[str, float]] = None,
    mission: str = "general",
) -> List[dict]:
    """
    Score and rank assets. Returns list sorted by final_score descending,
    with rank, priority_label, and action appended.
    """
    overrides = operator_overrides or {}
    mission_mults = MISSION_MULTIPLIERS.get(mission, {})

    scored = []
    for asset in assets:
        mil_cls = asset.get("military_class", "default")
        base = _BASE_SCORES.get(mil_cls, _BASE_SCORES["default"])
        cw = _conf_weight(asset.get("confidence", 0.5))
        pw = _proximity_weight(asset, assets)
        ow = overrides.get(mil_cls, 1.0)
        mw = mission_mults.get(mil_cls, 1.0)
        final = min(10.0, base * cw * pw * ow * mw)

        scored.append({
            **asset,
            "final_score": round(final, 3),
            "base_score": round(base, 2),
            "confidence_weight": cw,
            "proximity_weight": pw,
            "operator_weight": ow,
            "mission_weight": mw,
            "priority_label": _priority_label(final),
            "action": _ACTIONS.get(mil_cls, _ACTIONS["default"]),
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    for i, s in enumerate(scored, 1):
        s["rank"] = i
    return scored
