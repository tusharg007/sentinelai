"""Temporal change detection endpoint."""
import io
from typing import Optional
import numpy as np
from PIL import Image
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Request
from app.core.imaging import load_image
from app.services.change import analyze

router = APIRouter()

@router.post("/", summary="Detect changes between satellite passes")
async def detect_changes(
    request: Request,
    before: UploadFile = File(..., description="Earlier pass T1"),
    after:  UploadFile = File(..., description="Later pass T2"),
    sensitivity: float = Form(default=0.35, ge=0.10, le=0.80),
    return_visuals: bool = Form(default=True),
):
    before_raw = await before.read()
    after_raw  = await after.read()
    try:
        before_pil = Image.open(io.BytesIO(before_raw)).convert("RGB")
        after_pil  = Image.open(io.BytesIO(after_raw)).convert("RGB")
    except Exception:
        raise HTTPException(400, "Cannot decode one or both images")

    w, h = before_pil.size
    after_pil = after_pil.resize((w, h))

    before_np = np.array(before_pil)
    after_np  = np.array(after_pil)

    reg = request.app.state.registry
    change_model = reg.get("change_backbone")

    result = analyze(
        before_np, after_np,
        before_pil if change_model else None,
        after_pil  if change_model else None,
        change_model,
        reg.device,
        sensitivity=sensitivity,
        return_visuals=return_visuals,
    )
    return result
