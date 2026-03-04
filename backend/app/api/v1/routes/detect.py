"""Military asset detection endpoint."""
import io
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Request
from app.core.imaging import load_image
from app.services.detector import MilitaryDetector

router = APIRouter()

@router.post("/", summary="Detect military assets")
async def detect(
    request: Request,
    file: UploadFile = File(..., description="EO/IR/SAR imagery"),
    confidence: float = Form(default=0.25, ge=0.05, le=0.95),
    iou: float = Form(default=0.45, ge=0.1, le=0.9),
    mission: str = Form(default="general"),
    annotate: bool = Form(default=True),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    raw = await file.read()
    if len(raw) > request.app.state.registry._store.get("_max_bytes", 64*1024*1024):
        raise HTTPException(413, "Image too large")

    reg = request.app.state.registry
    if not reg.has("detector"):
        raise HTTPException(503, "Detector model not loaded — check server logs")

    img = load_image(raw)
    det = MilitaryDetector(reg.get("detector"), reg.device)
    return det.run(img, conf=confidence, iou=iou, mission=mission, annotate=annotate)
