"""
AuricVision — Service-layer unit tests (no server needed).
Run:  pytest backend/tests/ -v --tb=short
"""
import numpy as np
import pytest
from PIL import Image


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def make_rgb(h=256, w=256, seed=42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(40, 220, (h, w, 3), dtype=np.uint8)


# ─────────────────────────────────────────────────────────────
#  Imaging utilities
# ─────────────────────────────────────────────────────────────
class TestImaging:
    def test_encode_b64_returns_str(self):
        import sys; sys.path.insert(0, ".")
        from backend.app.core.imaging import encode_b64
        img = make_rgb()
        result = encode_b64(img)
        assert isinstance(result, str) and len(result) > 100

    def test_make_strip_width(self):
        from backend.app.core.imaging import make_strip
        a = make_rgb(200, 300)
        b = make_rgb(200, 300)
        strip = make_strip(a, b, labels=["A", "B"])
        assert strip.shape[1] > strip.shape[0]   # wider than tall


# ─────────────────────────────────────────────────────────────
#  Fusion
# ─────────────────────────────────────────────────────────────
class TestFusion:
    def test_simulate_ir_shape(self):
        from backend.app.services.fusion import simulate_ir
        rgb = make_rgb()
        ir = simulate_ir(rgb)
        assert ir.shape == rgb.shape

    def test_simulate_sar_shape(self):
        from backend.app.services.fusion import simulate_sar
        rgb = make_rgb()
        sar = simulate_sar(rgb)
        assert sar.shape == rgb.shape

    def test_fuse_output_range(self):
        from backend.app.services.fusion import fuse
        eo = make_rgb(seed=1); ir = make_rgb(seed=2); sar = make_rgb(seed=3)
        out = fuse(eo, ir, sar)
        assert out.dtype == np.uint8
        assert 0 <= out.min() and out.max() <= 255
        assert out.shape == eo.shape

    def test_fuse_weight_normalisation(self):
        from backend.app.services.fusion import fuse
        eo = make_rgb(seed=10); ir = make_rgb(seed=11); sar = make_rgb(seed=12)
        # unnormalised weights should still work
        out = fuse(eo, ir, sar, w_eo=5, w_ir=3, w_sar=2)
        assert out.shape == eo.shape

    def test_fuse_zero_weight_raises(self):
        from backend.app.services.fusion import fuse
        with pytest.raises(ValueError):
            fuse(make_rgb(), make_rgb(), make_rgb(), w_eo=0, w_ir=0, w_sar=0)


# ─────────────────────────────────────────────────────────────
#  Geospatial
# ─────────────────────────────────────────────────────────────
class TestGeospatial:
    def test_center_pixel_maps_to_center_coord(self):
        from backend.app.services.geospatial import pixel_to_wgs84
        lat, lon = pixel_to_wgs84(320, 240, 640, 480,
                                   lat_min=48.0, lat_max=49.0,
                                   lon_min=31.0, lon_max=32.0)
        assert abs(lat - 48.5) < 0.01
        assert abs(lon - 31.5) < 0.01

    def test_top_left_corner(self):
        from backend.app.services.geospatial import pixel_to_wgs84
        lat, lon = pixel_to_wgs84(0, 0, 100, 100, 48.0, 49.0, 31.0, 32.0)
        assert abs(lat - 49.0) < 0.01
        assert abs(lon - 31.0) < 0.01

    def test_mgrs_format_nonempty(self):
        from backend.app.services.geospatial import wgs84_to_mgrs
        mgrs = wgs84_to_mgrs(48.3794, 31.1656)
        assert isinstance(mgrs, str) and len(mgrs) > 5

    def test_footprint_calculation(self):
        from backend.app.services.geospatial import bbox_footprint_m2
        area = bbox_footprint_m2(0, 0, 100, 50, gsd_m=0.5)
        assert abs(area - 100*50*0.25) < 1.0   # 100px * 50px * (0.5m)^2

    def test_geolocate_preserves_count(self):
        from backend.app.services.geospatial import geolocate_detections
        dets = [
            {"asset_id":"TGT-001","military_class":"tank","confidence":0.9,
             "threat_score":7.5,"bbox":{"x1":10,"y1":10,"x2":50,"y2":50}},
            {"asset_id":"TGT-002","military_class":"radar_array","confidence":0.8,
             "threat_score":9.0,"bbox":{"x1":100,"y1":100,"x2":200,"y2":150}},
        ]
        results = geolocate_detections(dets, 640, 480, 48.0, 49.0, 31.0, 32.0, 0.5)
        assert len(results) == 2
        for r in results:
            assert "lat" in r and "lon" in r and "mgrs" in r


# ─────────────────────────────────────────────────────────────
#  Threat engine
# ─────────────────────────────────────────────────────────────
class TestThreatEngine:
    def _make_assets(self):
        return [
            {"asset_id":"A","military_class":"missile_launcher","confidence":0.95,
             "threat_score":9.5,"lat":48.3,"lon":31.2},
            {"asset_id":"B","military_class":"supply_truck","confidence":0.80,
             "threat_score":3.5,"lat":48.31,"lon":31.21},
        ]

    def test_high_value_ranks_first(self):
        from backend.app.services.threat import prioritize
        ranked = prioritize(self._make_assets())
        assert ranked[0]["military_class"] == "missile_launcher"

    def test_rank_field_sequential(self):
        from backend.app.services.threat import prioritize
        ranked = prioritize(self._make_assets())
        assert [r["rank"] for r in ranked] == list(range(1, len(ranked)+1))

    def test_operator_override_boosts(self):
        from backend.app.services.threat import prioritize
        assets = [{"asset_id":"X","military_class":"supply_truck",
                   "confidence":0.9,"threat_score":3.5,"lat":None,"lon":None}]
        normal = prioritize(assets)[0]["final_score"]
        boosted = prioritize(assets, operator_overrides={"supply_truck":2.5})[0]["final_score"]
        assert boosted > normal

    def test_mission_context_sead(self):
        from backend.app.services.threat import prioritize
        assets = [{"asset_id":"R","military_class":"radar_array",
                   "confidence":0.85,"threat_score":9.0,"lat":None,"lon":None}]
        base   = prioritize(assets, mission="general")[0]["final_score"]
        sead   = prioritize(assets, mission="sead")[0]["final_score"]
        assert sead > base


# ─────────────────────────────────────────────────────────────
#  Change detection
# ─────────────────────────────────────────────────────────────
class TestChangeDetection:
    def test_identical_images_low_change(self):
        from backend.app.services.change import _pixel_change_map
        img = make_rgb()
        cm = _pixel_change_map(img, img)
        assert cm.mean() < 0.05   # near zero change

    def test_opposite_images_high_change(self):
        from backend.app.services.change import _pixel_change_map
        black = np.zeros((128,128,3), dtype=np.uint8)
        white = np.full((128,128,3), 255, dtype=np.uint8)
        cm = _pixel_change_map(black, white)
        assert cm.mean() > 0.8

    def test_change_map_normalised(self):
        from backend.app.services.change import _pixel_change_map
        a = make_rgb(seed=1); b = make_rgb(seed=2)
        cm = _pixel_change_map(a, b)
        assert 0.0 <= cm.min() and cm.max() <= 1.0

    def test_find_regions_structure(self):
        from backend.app.services.change import _find_regions
        # bright block = significant change
        cm = np.zeros((256, 256), dtype=np.float32)
        cm[60:120, 80:160] = 0.9
        regions = _find_regions(cm, threshold=0.5)
        assert len(regions) >= 1
        assert "bbox" in regions[0] and "magnitude" in regions[0]

    def test_full_analyze_no_model(self):
        from backend.app.services.change import analyze
        a = make_rgb(seed=1); b = make_rgb(seed=2)
        result = analyze(a, b, None, None, None, "cpu",
                         sensitivity=0.35, return_visuals=False)
        assert "regions" in result
        assert "global_score" in result
        assert isinstance(result["type_counts"], dict)


# ─────────────────────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────────────────────
class TestConfig:
    def test_device_valid(self):
        from backend.app.core.config import settings
        assert settings.device in ("cpu", "cuda", "mps")

    def test_taxonomy_structure(self):
        from backend.app.core.config import ASSET_TAXONOMY
        for k, v in ASSET_TAXONOMY.items():
            assert len(v) == 2
            assert isinstance(v[0], str)
            assert isinstance(v[1], float)

    def test_all_mission_keys(self):
        from backend.app.core.config import MISSION_MULTIPLIERS
        for key in ("general", "anti_armor", "sead", "maritime"):
            assert key in MISSION_MULTIPLIERS
