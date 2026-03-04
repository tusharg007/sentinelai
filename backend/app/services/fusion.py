"""
ModalFusion — fuses EO, IR, and SAR imagery using
weighted channel-attention + CLAHE contrast enhancement.

Production path: replace weighted blend with a learned
CMX / TokenFusion cross-modal transformer.
"""
from typing import Tuple
import cv2
import numpy as np
from app.core.imaging import encode_b64, make_strip


def simulate_ir(rgb: np.ndarray) -> np.ndarray:
    """Approximate LWIR thermal from RGB via luminance + CLAHE + INFERNO palette."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    thermal = cv2.applyColorMap(enhanced, cv2.COLORMAP_INFERNO)
    return cv2.cvtColor(thermal, cv2.COLOR_BGR2RGB)


def simulate_sar(rgb: np.ndarray) -> np.ndarray:
    """
    Approximate SAR amplitude from RGB:
    1. Convert to grayscale (intensity channel)
    2. Add Rayleigh-distributed speckle noise
    3. Apply simplified Lee filter (local mean smoothing)
    4. CFAR-style edge enhancement
    """
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    rng = np.random.default_rng(seed=42)
    speckle = rng.rayleigh(scale=7.0, size=gray.shape).astype(np.float32)
    noisy = np.clip(gray + speckle - 3.5, 0, 255)
    smoothed = cv2.GaussianBlur(noisy, (5, 5), 0)
    edges = cv2.Canny(smoothed.astype(np.uint8), 25, 75)
    enhanced = cv2.addWeighted(smoothed, 0.88, edges.astype(np.float32), 0.12, 0)
    out = cv2.cvtColor(enhanced.astype(np.uint8), cv2.COLOR_GRAY2RGB)
    return out


def fuse(
    eo: np.ndarray,
    ir: np.ndarray,
    sar: np.ndarray,
    w_eo: float = 0.50,
    w_ir: float = 0.30,
    w_sar: float = 0.20,
) -> np.ndarray:
    """
    Weighted channel-attention fusion.
    Normalise weights → blend → CLAHE on L channel.
    """
    total = w_eo + w_ir + w_sar
    if total < 1e-6:
        raise ValueError("At least one fusion weight must be positive.")
    w_eo, w_ir, w_sar = w_eo/total, w_ir/total, w_sar/total

    blended = (
        w_eo * eo.astype(np.float32) +
        w_ir * ir.astype(np.float32) +
        w_sar * sar.astype(np.float32)
    )
    blended = np.clip(blended, 0, 255).astype(np.uint8)

    # Adaptive histogram equalisation on luminance
    lab = cv2.cvtColor(blended, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def build_comparison_strip(eo, ir, sar, fused) -> str:
    strip = make_strip(eo, ir, sar, fused,
                       labels=["EO", "IR", "SAR", "FUSED"])
    return encode_b64(cv2.cvtColor(strip, cv2.COLOR_BGR2RGB))
