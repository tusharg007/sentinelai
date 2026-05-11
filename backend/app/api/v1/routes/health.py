import platform
import torch
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/health", summary="Platform health check")
async def health(request: Request):
    reg = getattr(request.app.state, "registry", None)
    gpu = {}
    if torch.cuda.is_available():
        gpu = {
            "name": torch.cuda.get_device_name(0),
            "memory_allocated_gb": round(torch.cuda.memory_allocated() / 1e9, 3),
            "memory_reserved_gb":  round(torch.cuda.memory_reserved() / 1e9, 3),
        }
    return {
        "status": "operational",
        "platform": "AuricVision Defense Intelligence Platform",
        "version": "1.0.0",
        "device": reg.device if reg else "unknown",
        "loaded_models": reg.loaded if reg else [],
        "gpu": gpu,
        "torch": torch.__version__,
        "python": platform.python_version(),
    }
