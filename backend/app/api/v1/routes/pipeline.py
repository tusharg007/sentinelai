"""Full intelligence pipeline — runs all modules on one image."""
import io, time
from typing import Optional
import numpy as np
from PIL import Image
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Request
from app.core.imaging import load_image
from app.services.geospatial import geolocate_detections, wgs84_to_mgrs
from app.services.threat import prioritize

router = APIRouter()

@router.post("/", summary="Full end-to-end intelligence pipeline")
async def full_pipeline(
    request: Request,
    file: UploadFile = File(...),
    confidence: float = Form(default=0.25, ge=0.05, le=0.95),
    lat_min: float = Form(default=48.200),
    lat_max: float = Form(default=48.400),
    lon_min: float = Form(default=31.100),
    lon_max: float = Form(default=31.300),
    gsd_m: float = Form(default=0.5),
    mission: str = Form(default="general"),
):
    t0 = time.perf_counter()
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    raw = await file.read()
    img = load_image(raw)
    img_h, img_w = img.shape[:2]

    reg = request.app.state.registry
    errors = {}
    raw_assets = []
    detection_summary = None

    # ── Step 1: Detect ─────────────────────────────────────────────────────
    try:
        if not reg.has("detector"):
            raise RuntimeError("Detector not loaded")
        from app.services.detector import MilitaryDetector
        det = MilitaryDetector(reg.get("detector"), reg.device)
        dr = det.run(img, conf=confidence, mission=mission, annotate=True)
        raw_assets = [
            {
                "asset_id": a.asset_id,
                "military_class": a.military_class,
                "confidence": a.confidence,
                "threat_score": a.threat_score,
                "threat_level": a.threat_level,
                "bbox": {"x1":a.bbox.x1,"y1":a.bbox.y1,"x2":a.bbox.x2,"y2":a.bbox.y2},
            }
            for a in dr.assets
        ]
        detection_summary = {
            "total": dr.total,
            "threat_counts": dr.threat_counts,
            "annotated_b64": dr.annotated_b64,
        }
    except Exception as e:
        errors["detection"] = str(e)

    # ── Step 2: Geolocate ──────────────────────────────────────────────────
    if raw_assets:
        raw_assets = geolocate_detections(
            raw_assets, img_w, img_h,
            lat_min, lat_max, lon_min, lon_max, gsd_m,
        )

    # ── Step 3: Prioritize ─────────────────────────────────────────────────
    if raw_assets:
        raw_assets = prioritize(raw_assets, mission=mission)

    # ── Mission summary ────────────────────────────────────────────────────
    tc = (detection_summary or {}).get("threat_counts", {})
    sc_lat = (lat_min + lat_max) / 2
    sc_lon = (lon_min + lon_max) / 2
    top = raw_assets[0] if raw_assets else {}

    mission_summary = {
        "total_assets": len(raw_assets),
        "threat_counts": tc,
        "top_asset": top.get("military_class", "none"),
        "top_score": top.get("final_score", 0),
        "action": top.get("action", "No assets detected"),
        "mission": mission,
        "scene_center": {
            "lat": round(sc_lat, 6),
            "lon": round(sc_lon, 6),
            "mgrs": wgs84_to_mgrs(sc_lat, sc_lon),
        },
        "gsd_m": gsd_m,
    }

    return {
        "detection": detection_summary,
        "top_targets": raw_assets[:10],
        "mission_summary": mission_summary,
        "errors": errors,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "image_wh": [img_w, img_h],
    }
