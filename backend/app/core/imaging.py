"""
Shared imaging utilities — resize, encode, decode images consistently.
"""
import base64
import io
from typing import Tuple

import cv2
import numpy as np
from PIL import Image
from app.core.config import settings


def load_image(raw: bytes) -> np.ndarray:
    """Bytes → RGB numpy array, enforcing max side length."""
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = img.size
    max_side = settings.MAX_IMG_SIDE
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return np.array(img)


def encode_b64(arr: np.ndarray, quality: int = 88) -> str:
    """BGR or RGB numpy → base64 JPEG string."""
    if arr.shape[2] == 3:
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    else:
        bgr = arr
    _, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode()


def make_strip(*images: np.ndarray, labels: list = None) -> np.ndarray:
    """Horizontally concatenate images at uniform thumbnail width."""
    tw = min(min(img.shape[1] for img in images), 400)
    strips = []
    for i, img in enumerate(images):
        h, w = img.shape[:2]
        th = int(h * tw / w)
        thumb = cv2.resize(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), (tw, th))
        if labels and i < len(labels):
            cv2.putText(thumb, labels[i], (6, 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 220, 180), 1, cv2.LINE_AA)
        strips.append(thumb)
    return np.hstack(strips)
