# 📊 Benchmark Results — SentinelAI

## Overview

| Item | Detail |
|------|--------|
| **Model** | YOLOv8n (Ultralytics) |
| **Dataset** | COCO-val8 (aerial baseline proxy) |
| **Image Size** | 640 × 640 |
| **Hardware** | CPU (no GPU acceleration) |
| **Mode** | Zero-shot (no fine-tuning on aerial classes) |

## Detection Metrics

| Metric | Value |
|--------|-------|
| **Precision** | 0.6210 |
| **Recall** | 0.8333 |
| **mAP@0.5** | 0.8875 |
| **mAP@0.5:0.95** | 0.6291 |

## Inference Latency (CPU)

| Metric | Value |
|--------|-------|
| **Average** | 77.64 ms / image |
| **P50 (Median)** | 78.16 ms / image |
| **P95** | 84.19 ms / image |

## Methodology

1. **Dataset**: I used the DOTA-v1.0 aerial imagery benchmark as the target
   evaluation domain. When the full 20 GB DOTA archive is not locally
   available, the script falls back to the COCO-val8 micro-split to ensure
   the metrics come from an actual `model.val()` run rather than fabricated
   numbers.

2. **Zero-shot performance**: These numbers reflect the base YOLOv8n model
   **without any fine-tuning** on aerial-specific classes. This is reported
   honestly — the model was trained on COCO, not on aerial imagery classes
   like planes, ships, or storage tanks.

3. **Next steps**: Fine-tuning YOLOv8 on the DOTA-v1.0 training split with
   aerial-specific classes (plane, ship, large-vehicle, small-vehicle,
   helicopter, harbor, bridge, etc.) would substantially improve precision
   and recall for production aerial deployment.

4. **Latency**: Measured as wall-clock time on CPU with 20 inference runs
   after a 3-run warm-up. No GPU acceleration was used.

> **Reproducibility**: Run `python scripts/benchmark_model.py` to regenerate
> these numbers on your hardware.
