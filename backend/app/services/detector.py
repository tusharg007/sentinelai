"""
MilitaryDetector — wraps YOLO, maps classes to military taxonomy,
applies threat scoring, and renders tactical annotations.
"""
import time
from typing import List, Tuple

import cv2
import numpy as np
from loguru import logger

from app.core.config import settings, ASSET_TAXONOMY, MISSION_MULTIPLIERS
from app.core.imaging import encode_b64
from app.schemas.detection import DetectedAsset, BoundingBox, DetectionResponse


# Threat level thresholds
def _level(score: float) -> str:
    if score >= 8.5: return "critical"
    if score >= 6.5: return "high"
    if score >= 4.0: return "medium"
    return "low"


# Per-level draw colors (BGR)
_COLORS = {
    "critical": (30, 30, 220),
    "high":     (30, 120, 230),
    "medium":   (30, 200, 220),
    "low":      (30, 200, 80),
}


class MilitaryDetector:
    def __init__(self, model, device: str):
        self._model = model
        self._device = device

    def run(
        self,
        image: np.ndarray,
        conf: float = settings.DEFAULT_CONF,
        iou: float = settings.DEFAULT_IOU,
        max_det: int = settings.MAX_DETECTIONS,
        mission: str = "general",
        annotate: bool = True,
    ) -> DetectionResponse:
        t0 = time.perf_counter()
        h, w = image.shape[:2]

        results = self._model.predict(
            source=image,
            conf=conf,
            iou=iou,
            max_det=max_det,
            verbose=False,
            device=self._device,
        )
        r = results[0]

        mission_mults = MISSION_MULTIPLIERS.get(mission, {})
        assets: List[DetectedAsset] = []

        if r.boxes is not None and len(r.boxes):
            for idx, (box, cf, cls_id) in enumerate(zip(
                r.boxes.xyxy.cpu().numpy(),
                r.boxes.conf.cpu().numpy(),
                r.boxes.cls.cpu().numpy().astype(int),
            )):
                x1, y1, x2, y2 = box.tolist()
                area_frac = ((x2 - x1) * (y2 - y1)) / (w * h)
                raw_cls = r.names[cls_id]
                mil_cls, base_t = ASSET_TAXONOMY.get(raw_cls, ASSET_TAXONOMY["default"])

                # Confidence-adjusted threat score
                adj = min(10.0, base_t * (0.65 + 0.35 * float(cf)))
                # Mission context multiplier
                adj = min(10.0, adj * mission_mults.get(mil_cls, 1.0))

                assets.append(DetectedAsset(
                    asset_id=f"TGT-{idx+1:03d}",
                    raw_class=raw_cls,
                    military_class=mil_cls,
                    confidence=round(float(cf), 4),
                    threat_score=round(adj, 3),
                    threat_level=_level(adj),
                    bbox=BoundingBox(
                        x1=round(x1, 1), y1=round(y1, 1),
                        x2=round(x2, 1), y2=round(y2, 1),
                        x1n=round(x1/w, 4), y1n=round(y1/h, 4),
                        x2n=round(x2/w, 4), y2n=round(y2/h, 4),
                    ),
                    area_fraction=round(float(area_frac), 6),
                ))

        assets.sort(key=lambda a: a.threat_score, reverse=True)

        threat_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for a in assets:
            threat_counts[a.threat_level] += 1

        annotated_b64 = None
        if annotate and assets:
            annotated_b64 = self._render(image.copy(), assets, w, h, threat_counts)

        ms = round((time.perf_counter() - t0) * 1000, 2)
        return DetectionResponse(
            assets=assets,
            total=len(assets),
            threat_counts=threat_counts,
            top_threat=assets[0].military_class if assets else None,
            annotated_b64=annotated_b64,
            latency_ms=ms,
            image_wh=[w, h],
        )

    def _render(self, img: np.ndarray, assets: List[DetectedAsset],
                w: int, h: int, counts: dict) -> str:
        vis = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        for a in assets:
            color = _COLORS[a.threat_level]
            b = a.bbox
            x1, y1, x2, y2 = int(b.x1), int(b.y1), int(b.x2), int(b.y2)

            # Main box
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)

            # Corner tick marks (tactical style)
            sz = max(6, min(14, (x2-x1)//6))
            for px, py, dx, dy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(vis, (px, py), (px + dx*sz, py), color, 2)
                cv2.line(vis, (px, py), (px, py + dy*sz), color, 2)

            # Label pill
            lbl = f"{a.asset_id} {a.military_class.replace('_',' ').upper()} {a.threat_score:.1f}"
            (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            cv2.rectangle(vis, (x1, y1 - th - 6), (x1 + tw + 6, y1), color, -1)
            cv2.putText(vis, lbl, (x1+3, y1-3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0,0,0), 1, cv2.LINE_AA)

        # HUD bar
        hud = (f"ASSETS: {len(assets)}  "
               f"CRITICAL:{counts['critical']}  HIGH:{counts['high']}  "
               f"MED:{counts['medium']}  LOW:{counts['low']}")
        cv2.rectangle(vis, (0,0), (w, 26), (0,0,0), -1)
        cv2.putText(vis, hud, (8, 17), cv2.FONT_HERSHEY_SIMPLEX,
                    0.52, (0,220,180), 1, cv2.LINE_AA)

        return encode_b64(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
