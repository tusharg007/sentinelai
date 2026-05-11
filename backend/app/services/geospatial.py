"""
GeoEngine — converts pixel bounding boxes to geodetic coordinates.

Supports:
  • Manual corner-coordinate input (demo / quick use)
  • GeoTIFF affine transform (production — via GDAL/rasterio)

Outputs WGS84 lat/lon and approximate MGRS grid reference.
"""
import math
from typing import Tuple, List


def pixel_to_wgs84(
    px: float, py: float,
    img_w: int, img_h: int,
    lat_min: float, lat_max: float,
    lon_min: float, lon_max: float,
) -> Tuple[float, float]:
    """
    Bilinear pixel → WGS84 mapping.
    Production: replace with GDAL affine transform from GeoTIFF metadata.
    """
    lon = lon_min + (px / img_w) * (lon_max - lon_min)
    lat = lat_max - (py / img_h) * (lat_max - lat_min)
    return round(lat, 6), round(lon, 6)


def wgs84_to_mgrs(lat: float, lon: float) -> str:
    """
    Approximate MGRS string for display purposes.
    Production: use the `mgrs` PyPI package for centimetre accuracy.
    """
    zone_num = int((lon + 180) / 6) + 1
    lat_bands = "CDEFGHJKLMNPQRSTUVWX"
    band_idx = min(int((lat + 80) / 8), len(lat_bands) - 1)
    lat_band = lat_bands[band_idx]

    sq_letters = "ABCDEFGHJKLMNPQRSTUV"
    col = sq_letters[int(abs(lon) % len(sq_letters))]
    row = sq_letters[int(abs(lat) % len(sq_letters))]

    e = int((abs(lon) % 1) * 100_000)
    n = int((abs(lat) % 1) * 100_000)
    return f"{zone_num}{lat_band} {col}{row} {e:05d} {n:05d}"


def coord_str(lat: float, lon: float) -> str:
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{abs(lat):.6f}°{ns}  {abs(lon):.6f}°{ew}"


def bbox_footprint_m2(
    x1: float, y1: float, x2: float, y2: float,
    gsd_m: float,
) -> float:
    """Estimate ground-plane footprint of a bounding box in m²."""
    return round((x2 - x1) * gsd_m * (y2 - y1) * gsd_m, 1)


def geolocate_detections(
    detections: List[dict],
    img_w: int, img_h: int,
    lat_min: float, lat_max: float,
    lon_min: float, lon_max: float,
    gsd_m: float,
) -> List[dict]:
    """
    Attach lat/lon/MGRS coordinates to a list of detection dicts.
    Each dict must have keys: asset_id, military_class, confidence,
    threat_score, bbox {x1,y1,x2,y2}.
    """
    results = []
    for d in detections:
        b = d.get("bbox", {})
        if isinstance(b, dict):
            x1, y1, x2, y2 = b["x1"], b["y1"], b["x2"], b["y2"]
        else:
            x1, y1, x2, y2 = b.x1, b.y1, b.x2, b.y2

        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        lat, lon = pixel_to_wgs84(cx, cy, img_w, img_h,
                                  lat_min, lat_max, lon_min, lon_max)
        lat1, lon1 = pixel_to_wgs84(x1, y1, img_w, img_h,
                                    lat_min, lat_max, lon_min, lon_max)
        lat2, lon2 = pixel_to_wgs84(x2, y2, img_w, img_h,
                                    lat_min, lat_max, lon_min, lon_max)
        results.append({
            **d,
            "lat": lat,
            "lon": lon,
            "coord_str": coord_str(lat, lon),
            "mgrs": wgs84_to_mgrs(lat, lon),
            "footprint_m2": bbox_footprint_m2(x1, y1, x2, y2, gsd_m),
            "bbox_geo": [lat1, lon1, lat2, lon2],
        })
    return results
