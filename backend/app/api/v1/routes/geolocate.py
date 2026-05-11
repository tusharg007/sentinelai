"""Geospatial targeting endpoint — pixel detections → GPS/MGRS."""
import io, json, time
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from PIL import Image
from app.services.geospatial import geolocate_detections

router = APIRouter()

@router.post("/", summary="Geolocate detected targets")
async def geolocate(
    file: UploadFile = File(...),
    detections_json: str = Form(..., description='JSON list from /detect response assets array'),
    lat_min: float = Form(default=48.200),
    lat_max: float = Form(default=48.400),
    lon_min: float = Form(default=31.100),
    lon_max: float = Form(default=31.300),
    gsd_m: float = Form(default=0.5, ge=0.05, le=100.0),
):
    t0 = time.perf_counter()
    try:
        dets = json.loads(detections_json)
        if not isinstance(dets, list): raise ValueError
    except Exception:
        raise HTTPException(400, "detections_json must be a JSON array")

    raw = await file.read()
    try:
        img = Image.open(io.BytesIO(raw))
        img_w, img_h = img.size
    except Exception:
        raise HTTPException(400, "Cannot decode image")

    # Normalise detection dicts — accept both schema objects and plain dicts
    flat_dets = []
    for d in dets[:200]:
        b = d.get("bbox", {})
        if isinstance(b, dict):
            x1,y1,x2,y2 = b.get("x1",0),b.get("y1",0),b.get("x2",img_w),b.get("y2",img_h)
        elif isinstance(b, list) and len(b) >= 4:
            x1,y1,x2,y2 = b[:4]
        else:
            x1,y1,x2,y2 = 0,0,img_w,img_h
        flat_dets.append({
            "asset_id": d.get("asset_id", f"TGT-{len(flat_dets)+1:03d}"),
            "military_class": d.get("military_class", d.get("asset", "unknown")),
            "confidence": d.get("confidence", 0.5),
            "threat_score": d.get("threat_score", 4.0),
            "bbox": {"x1":x1,"y1":y1,"x2":x2,"y2":y2},
        })

    targets = geolocate_detections(
        flat_dets, img_w, img_h,
        lat_min, lat_max, lon_min, lon_max, gsd_m,
    )
    targets.sort(key=lambda t: t["threat_score"], reverse=True)

    from app.services.geospatial import wgs84_to_mgrs
    sc_lat = (lat_min+lat_max)/2
    sc_lon = (lon_min+lon_max)/2

    return {
        "targets": targets,
        "total": len(targets),
        "crs": "WGS84 (EPSG:4326)",
        "gsd_m": gsd_m,
        "scene_bounds": {"lat_min":lat_min,"lat_max":lat_max,"lon_min":lon_min,"lon_max":lon_max},
        "scene_center": {"lat":round(sc_lat,6),"lon":round(sc_lon,6),"mgrs":wgs84_to_mgrs(sc_lat,sc_lon)},
        "latency_ms": round((time.perf_counter()-t0)*1000, 2),
    }
