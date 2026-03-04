"""Target prioritization endpoint."""
import time
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.threat import prioritize

router = APIRouter()

class AssetIn(BaseModel):
    asset_id: str = "TGT-001"
    military_class: str
    confidence: float = Field(..., ge=0, le=1)
    threat_score: float = Field(..., ge=0, le=10)
    lat: Optional[float] = None
    lon: Optional[float] = None

class PrioritizeRequest(BaseModel):
    assets: List[AssetIn]
    operator_overrides: Optional[Dict[str, float]] = None
    mission: str = "general"

@router.post("/", summary="Rank targets by threat priority")
async def prioritize_targets(req: PrioritizeRequest):
    t0 = time.perf_counter()
    if not req.assets:
        raise HTTPException(400, "No assets provided")
    if len(req.assets) > 500:
        raise HTTPException(400, "Max 500 assets per request")

    asset_dicts = [a.model_dump() for a in req.assets]
    ranked = prioritize(asset_dicts, req.operator_overrides, req.mission)

    overrides_applied = [f"{k}×{v}" for k,v in (req.operator_overrides or {}).items()]

    return {
        "targets": ranked,
        "total": len(ranked),
        "method": "MultiFactorThreat: base × confidence × proximity × operator × mission",
        "overrides_applied": overrides_applied,
        "mission": req.mission,
        "latency_ms": round((time.perf_counter()-t0)*1000, 2),
    }
