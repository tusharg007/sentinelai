"""
ChangeEngine — detects new/moved/removed assets between satellite passes.

Two-tier approach:
  1. Pixel-level multi-scale luminance difference map
  2. Semantic ViT (CLIP encoder) similarity score — detects
     scene-level change even with minor mis-registration
"""
import time
from typing import Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from app.core.imaging import encode_b64, make_strip


def _pixel_change_map(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """
    Multi-scale luminance + colour difference normalised to [0, 1].
    Uses two Gaussian scales to separate coarse (structural) from
    fine (surface) changes.
    """
    b = before.astype(np.float32)
    a = after.astype(np.float32)

    lum_b = 0.299*b[:,:,0] + 0.587*b[:,:,1] + 0.114*b[:,:,2]
    lum_a = 0.299*a[:,:,0] + 0.587*a[:,:,1] + 0.114*a[:,:,2]
    lum_diff = np.abs(lum_a - lum_b)

    # Coarse and fine scales
    coarse = cv2.GaussianBlur(lum_diff, (21, 21), 0)
    fine   = cv2.GaussianBlur(lum_diff, (5, 5), 0)
    combined = 0.55 * coarse + 0.45 * fine

    # Normalise
    mn, mx = combined.min(), combined.max()
    return (combined - mn) / (mx - mn + 1e-7)


def _vit_scene_change(
    before_pil: Image.Image,
    after_pil: Image.Image,
    model,
    processor,
    device: str,
) -> float:
    """Cosine distance in CLIP embedding space: 0 = identical, 1 = fully changed."""
    try:
        inputs = processor(images=[before_pil, after_pil],
                           return_tensors="pt", padding=True)
        pv = inputs["pixel_values"].to(device)
        with torch.no_grad():
            feats = model.get_image_features(pixel_values=pv)
        feats = F.normalize(feats, dim=-1)
        sim = float(torch.dot(feats[0], feats[1]).item())
        return round(1.0 - sim, 4)
    except Exception:
        return 0.5   # conservative fallback


def _find_regions(change_map: np.ndarray, threshold: float) -> list:
    binary = (change_map > threshold).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = change_map.shape
    regions = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 150:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        mag = float(change_map[y:y+bh, x:x+bw].mean())
        regions.append({
            "bbox": [float(x), float(y), float(x+bw), float(y+bh)],
            "area": area,
            "area_fraction": round(area / (h*w), 6),
            "magnitude": round(mag, 4),
        })

    regions.sort(key=lambda r: r["magnitude"] * r["area"], reverse=True)
    return regions[:40]


def _classify_change(mag: float, area_frac: float) -> Tuple[str, str]:
    """Heuristic change type + significance from magnitude and area."""
    if mag > 0.65:
        ctype = "new_asset"
    elif mag > 0.50:
        ctype = "removed_asset"
    elif area_frac > 0.015:
        ctype = "construction"
    else:
        ctype = "moved_asset"
    sig = "high" if mag > 0.55 else ("medium" if mag > 0.38 else "low")
    return ctype, sig


def analyze(
    before: np.ndarray,
    after: np.ndarray,
    before_pil: Optional[Image.Image],
    after_pil: Optional[Image.Image],
    change_model: Optional[dict],
    device: str,
    sensitivity: float = 0.35,
    return_visuals: bool = True,
) -> dict:
    t0 = time.perf_counter()

    # Semantic score
    global_score = 0.5
    if change_model and before_pil and after_pil:
        global_score = _vit_scene_change(
            before_pil, after_pil,
            change_model["model"], change_model["processor"], device,
        )

    # Pixel map
    change_map = _pixel_change_map(before, after)
    raw_regions = _find_regions(change_map, threshold=sensitivity)

    regions = []
    type_counts = {"new_asset": 0, "removed_asset": 0, "moved_asset": 0, "construction": 0}

    for i, reg in enumerate(raw_regions):
        ctype, sig = _classify_change(reg["magnitude"], reg["area_fraction"])
        type_counts[ctype] += 1
        regions.append({
            "region_id": f"CHG-{i+1:03d}",
            "change_type": ctype,
            "magnitude": reg["magnitude"],
            "bbox": reg["bbox"],
            "area_fraction": reg["area_fraction"],
            "significance": sig,
        })

    heatmap_b64 = strip_b64 = None
    if return_visuals:
        hm = cv2.applyColorMap((change_map * 255).astype(np.uint8), cv2.COLORMAP_JET)
        # Draw boxes on heatmap
        _colors = {"new_asset":(0,0,255),"removed_asset":(0,165,255),
                   "construction":(0,200,0),"moved_asset":(200,200,0)}
        for reg in regions[:10]:
            x1,y1,x2,y2 = [int(v) for v in reg["bbox"]]
            c = _colors.get(reg["change_type"],(255,255,255))
            cv2.rectangle(hm,(x1,y1),(x2,y2),c,2)
        heatmap_b64 = encode_b64(cv2.cvtColor(hm, cv2.COLOR_BGR2RGB))

        diff_vis = cv2.applyColorMap((change_map*255).astype(np.uint8), cv2.COLORMAP_MAGMA)
        strip = make_strip(before, after, cv2.cvtColor(diff_vis, cv2.COLOR_BGR2RGB),
                           labels=["BEFORE T1","AFTER T2","CHANGE MAP"])
        strip_b64 = encode_b64(cv2.cvtColor(strip, cv2.COLOR_BGR2RGB))

    return {
        "regions": regions,
        "total": len(regions),
        "global_score": global_score,
        "type_counts": type_counts,
        "heatmap_b64": heatmap_b64,
        "strip_b64": strip_b64,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
