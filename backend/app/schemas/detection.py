"""Pydantic schemas for detection responses."""
from typing import List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: float; y1: float; x2: float; y2: float
    x1n: float; y1n: float; x2n: float; y2n: float  # normalised 0-1


class DetectedAsset(BaseModel):
    asset_id: str                                          # TGT-001
    raw_class: str                                         # COCO class
    military_class: str                                    # mapped label
    confidence: float = Field(..., ge=0, le=1)
    threat_score: float = Field(..., ge=0, le=10)
    threat_level: str                                      # critical|high|medium|low
    bbox: BoundingBox
    area_fraction: float


class DetectionResponse(BaseModel):
    assets: List[DetectedAsset]
    total: int
    threat_counts: dict
    top_threat: Optional[str]
    annotated_b64: Optional[str]
    latency_ms: float
    image_wh: List[int]


class GeoTarget(BaseModel):
    asset_id: str
    military_class: str
    confidence: float
    threat_score: float
    lat: float
    lon: float
    coord_str: str
    mgrs: str
    footprint_m2: float
    bbox_geo: List[float]          # [lat1,lon1,lat2,lon2]


class GeoResponse(BaseModel):
    targets: List[GeoTarget]
    total: int
    crs: str
    gsd_m: float
    scene_bounds: dict
    latency_ms: float


class PrioritizedTarget(BaseModel):
    rank: int
    asset_id: str
    military_class: str
    final_score: float
    base_score: float
    confidence_weight: float
    proximity_weight: float
    operator_weight: float
    mission_weight: float
    priority_label: str
    action: str
    lat: Optional[float]
    lon: Optional[float]


class PrioritizationResponse(BaseModel):
    targets: List[PrioritizedTarget]
    total: int
    method: str
    overrides_applied: List[str]
    latency_ms: float


class ChangeRegion(BaseModel):
    region_id: str
    change_type: str
    magnitude: float
    bbox: List[float]
    area_fraction: float
    significance: str


class ChangeResponse(BaseModel):
    regions: List[ChangeRegion]
    total: int
    global_score: float
    type_counts: dict
    heatmap_b64: Optional[str]
    strip_b64: Optional[str]
    latency_ms: float


class FusionResponse(BaseModel):
    detections: List[dict]
    total: int
    modalities: List[str]
    fusion_method: str
    confidence_gain_pct: float
    strip_b64: Optional[str]
    latency_ms: float


class IntelReport(BaseModel):
    """Full pipeline unified report."""
    detection: Optional[dict]
    top_targets: List[dict]
    mission_summary: dict
    errors: dict
    latency_ms: float
    image_wh: List[int]
