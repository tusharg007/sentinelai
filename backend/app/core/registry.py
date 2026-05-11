"""
ModelRegistry — lazy-loads, caches, and releases all AI models.
Thread-safe singleton pattern; models live in app.state.registry.
"""
import asyncio
from typing import Any, Dict, Optional
import torch
from loguru import logger
from app.core.config import settings


class ModelRegistry:
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._device = settings.device
        self._lock = asyncio.Lock()

    # ── Public interface ──────────────────────────────────────────────────
    async def load_all(self):
        loop = asyncio.get_event_loop()
        tasks = []
        if "detector" in settings.ENABLE_MODELS:
            tasks.append(loop.run_in_executor(None, self._load_detector))
        if "change_backbone" in settings.ENABLE_MODELS:
            tasks.append(loop.run_in_executor(None, self._load_change_backbone))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Model load warning (non-fatal): {r}")

    def get(self, name: str) -> Optional[Any]:
        return self._store.get(name)

    def has(self, name: str) -> bool:
        return name in self._store

    @property
    def loaded(self) -> list:
        return list(self._store.keys())

    @property
    def device(self) -> str:
        return self._device

    async def release(self):
        self._store.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Model memory released.")

    # ── Loaders ───────────────────────────────────────────────────────────
    def _load_detector(self):
        try:
            from ultralytics import YOLO
            logger.info(f"Loading detector: {settings.DETECTOR_MODEL}")
            model = YOLO(settings.DETECTOR_MODEL)
            self._store["detector"] = model
            logger.success(f"✓ Detector ready ({settings.DETECTOR_MODEL})")
        except Exception as e:
            logger.error(f"Detector load failed: {e}")

    def _load_change_backbone(self):
        try:
            from transformers import CLIPModel, CLIPProcessor
            logger.info(f"Loading change backbone: {settings.CHANGE_BACKBONE}")
            model = CLIPModel.from_pretrained(settings.CHANGE_BACKBONE)
            proc  = CLIPProcessor.from_pretrained(settings.CHANGE_BACKBONE)
            model.eval()
            if self._device not in ("cpu",):
                model = model.to(self._device)
            self._store["change_backbone"] = {"model": model, "processor": proc}
            logger.success("✓ Change backbone (ViT-B/32) ready")
        except Exception as e:
            logger.error(f"Change backbone load failed: {e}")
