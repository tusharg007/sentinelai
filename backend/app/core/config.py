"""
AuricVision — Application Configuration
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = "AuricVision"
    VERSION: str = "1.0.0"
    API_VERSION: str = "v1"
    ENV: str = Field(default="development")
    DEVICE: str = Field(default="auto")

    @property
    def device(self) -> str:
        if self.DEVICE != "auto":
            return self.DEVICE
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    SECRET_KEY: str = Field(default="change-me-in-production-32chars!!")
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "https://auricvision.io"]
    API_KEY_HEADER: str = "X-AuricVision-Key"

    DETECTOR_MODEL: str = "yolov8n.pt"
    CHANGE_BACKBONE: str = "openai/clip-vit-base-patch32"
    MODEL_CACHE_DIR: str = "/tmp/auric_models"
    ENABLE_MODELS: List[str] = Field(default=["detector", "change_backbone"])

    DEFAULT_CONF: float = 0.25
    DEFAULT_IOU: float = 0.45
    MAX_DETECTIONS: int = 300
    MAX_IMG_SIDE: int = 1280
    MAX_UPLOAD_MB: int = 64
    DEFAULT_GSD_M: float = 0.5
    WGS84_EPSG: str = "EPSG:4326"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

ASSET_TAXONOMY: dict = {
    "airplane":       ("fighter_aircraft",    8.5),
    "car":            ("armored_vehicle",      6.0),
    "truck":          ("supply_truck",         3.5),
    "bus":            ("command_vehicle",      7.5),
    "boat":           ("warship",              7.5),
    "train":          ("missile_launcher",     9.5),
    "motorcycle":     ("scout_vehicle",        4.0),
    "bicycle":        ("infantry",             2.0),
    "person":         ("personnel",            1.5),
    "stop sign":      ("radar_array",          8.5),
    "traffic light":  ("c2_node",              7.5),
    "fire hydrant":   ("ammo_cache",           5.0),
    "umbrella":       ("camouflage_net",       3.0),
    "backpack":       ("field_equipment",      2.5),
    "suitcase":       ("comms_kit",            4.0),
    "default":        ("unidentified_asset",   4.0),
}

MISSION_MULTIPLIERS: dict = {
    "anti_armor":   {"armored_vehicle": 1.4, "missile_launcher": 1.2, "supply_truck": 0.8},
    "sead":         {"radar_array": 1.5, "c2_node": 1.4, "fighter_aircraft": 1.2},
    "maritime":     {"warship": 1.4, "supply_truck": 0.9, "radar_array": 1.1},
    "general":      {},
}
