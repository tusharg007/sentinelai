"""
SentinelAI — Streamlit Demo
Runs standalone using the same backend services directly (no FastAPI needed).
Deploy free at: https://streamlit.io/cloud
"""

import io
import base64
import time
import numpy as np
import streamlit as st
from PIL import Image
import cv2

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SentinelAI — Battlefield Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=IBM+Plex+Mono&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Mono', monospace; }
.stApp { background: #020507; color: #c8dde8; }

h1, h2, h3 { font-family: 'Orbitron', monospace !important; color: #00ff88 !important; }

.metric-box {
    background: rgba(6,13,20,0.9);
    border: 1px solid #0e2233;
    border-radius: 4px;
    padding: 16px;
    text-align: center;
}
.metric-val { font-family: 'Orbitron', monospace; font-size: 2rem; font-weight: 900; }
.metric-lbl { font-size: 0.6rem; letter-spacing: 0.15em; color: #3a6080; text-transform: uppercase; }

.critical { color: #ff1a1a; text-shadow: 0 0 8px #ff1a1a; }
.high     { color: #ff6b00; text-shadow: 0 0 8px #ff6b00; }
.medium   { color: #ffd700; text-shadow: 0 0 8px #ffd700; }
.low      { color: #00ff88; text-shadow: 0 0 8px #00ff88; }

.target-card {
    background: rgba(6,13,20,0.8);
    border: 1px solid #0e2233;
    border-left: 2px solid #00ff88;
    border-radius: 3px;
    padding: 12px;
    margin-bottom: 8px;
    font-size: 0.75rem;
}
.hud-header {
    font-family: 'Orbitron', monospace;
    font-size: 0.55rem;
    letter-spacing: 0.2em;
    color: #3a6080;
    text-transform: uppercase;
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Asset taxonomy ─────────────────────────────────────────────────────────────
ASSET_TAXONOMY = {
    "airplane":      ("fighter_aircraft",   8.5),
    "car":           ("armored_vehicle",    6.0),
    "truck":         ("supply_truck",       3.5),
    "bus":           ("command_vehicle",    7.5),
    "boat":          ("warship",            7.5),
    "train":         ("missile_launcher",   9.5),
    "motorcycle":    ("scout_vehicle",      4.0),
    "bicycle":       ("infantry",           2.0),
    "person":        ("personnel",          1.5),
    "stop sign":     ("radar_array",        8.5),
    "traffic light": ("c2_node",            7.5),
    "fire hydrant":  ("ammo_cache",         5.0),
    "umbrella":      ("camouflage_net",     3.0),
    "backpack":      ("field_equipment",    2.5),
    "suitcase":      ("comms_kit",          4.0),
}

MISSION_MULTS = {
    "general":    {},
    "anti_armor": {"armored_vehicle": 1.4, "missile_launcher": 1.2},
    "sead":       {"radar_array": 1.5, "c2_node": 1.4, "fighter_aircraft": 1.2},
    "maritime":   {"warship": 1.4, "radar_array": 1.1},
}

ACTIONS = {
    "missile_launcher": "IMMEDIATE STRIKE — Time-critical target",
    "radar_array":      "PRIORITY STRIKE — Degrade C2 network",
    "c2_node":          "PRIORITY STRIKE — Disrupt command chain",
    "fighter_aircraft": "AIR INTERCEPT — Coordinate CAP",
    "command_vehicle":  "HIGH PRIORITY — Sever adversary coordination",
    "warship":          "MARITIME STRIKE — Coordinate naval assets",
    "armored_vehicle":  "ANTI-ARMOR TASKING — Brigade coordination",
}

LEVEL_COLORS = {"critical": "#ff1a1a", "high": "#ff6b00", "medium": "#ffd700", "low": "#00ff88"}

def threat_level(score):
    if score >= 8.5: return "critical"
    if score >= 6.5: return "high"
    if score >= 4.0: return "medium"
    return "low"

# ── Model loader ──────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading AI models...")
def load_models():
    from ultralytics import YOLO
    detector = YOLO("yolov8n.pt")
    try:
        from transformers import CLIPModel, CLIPProcessor
        clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        clip_proc  = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        clip_model.eval()
        return detector, {"model": clip_model, "processor": clip_proc}
    except Exception:
        return detector, None

# ── Detection ─────────────────────────────────────────────────────────────────
def run_detection(img_np, conf, mission):
    detector, _ = load_models()
    t0 = time.perf_counter()
    results = detector.predict(source=img_np, conf=conf, iou=0.45, verbose=False)
    r = results[0]
    h, w = img_np.shape[:2]
    mults = MISSION_MULTS.get(mission, {})
    assets = []
    if r.boxes is not None:
        for i, (box, cf, cls_id) in enumerate(zip(
            r.boxes.xyxy.cpu().numpy(),
            r.boxes.conf.cpu().numpy(),
            r.boxes.cls.cpu().numpy().astype(int)
        )):
            x1, y1, x2, y2 = box.tolist()
            raw = r.names[cls_id]
            mil_cls, base = ASSET_TAXONOMY.get(raw, ("unidentified_asset", 4.0))
            score = min(10.0, base * (0.65 + 0.35 * float(cf)) * mults.get(mil_cls, 1.0))
            assets.append({
                "asset_id": f"TGT-{i+1:03d}",
                "raw_class": raw,
                "military_class": mil_cls,
                "confidence": round(float(cf), 3),
                "threat_score": round(score, 2),
                "threat_level": threat_level(score),
                "bbox": [x1, y1, x2, y2],
                "action": ACTIONS.get(mil_cls, "CONTINUE ISR — Monitor and track"),
            })
    assets.sort(key=lambda a: a["threat_score"], reverse=True)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    return assets, ms

def annotate(img_np, assets):
    vis = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    colors = {"critical":(30,30,220),"high":(30,120,230),"medium":(30,200,220),"low":(30,200,80)}
    for a in assets:
        x1,y1,x2,y2 = [int(v) for v in a["bbox"]]
        c = colors[a["threat_level"]]
        cv2.rectangle(vis,(x1,y1),(x2,y2),c,2)
        sz = max(6, min(14,(x2-x1)//6))
        for px,py,dx,dy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
            cv2.line(vis,(px,py),(px+dx*sz,py),c,2)
            cv2.line(vis,(px,py),(px,py+dy*sz),c,2)
        lbl = f"{a['asset_id']} {a['military_class'].replace('_',' ').upper()} {a['threat_score']:.1f}"
        (tw,th),_ = cv2.getTextSize(lbl,cv2.FONT_HERSHEY_SIMPLEX,0.42,1)
        cv2.rectangle(vis,(x1,y1-th-6),(x1+tw+6,y1),c,-1)
        cv2.putText(vis,lbl,(x1+3,y1-3),cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,0,0),1,cv2.LINE_AA)
    counts = {l: sum(1 for a in assets if a["threat_level"]==l) for l in ["critical","high","medium","low"]}
    hud = f"ASSETS: {len(assets)}  CRITICAL:{counts['critical']}  HIGH:{counts['high']}  MED:{counts['medium']}  LOW:{counts['low']}"
    cv2.rectangle(vis,(0,0),(vis.shape[1],26),(0,0,0),-1)
    cv2.putText(vis,hud,(8,17),cv2.FONT_HERSHEY_SIMPLEX,0.52,(0,220,180),1,cv2.LINE_AA)
    return cv2.cvtColor(vis,cv2.COLOR_BGR2RGB)

def run_change(before_np, after_np):
    _, clip = load_models()
    b = before_np.astype(np.float32)
    a = after_np.astype(np.float32)
    lum_b = 0.299*b[:,:,0]+0.587*b[:,:,1]+0.114*b[:,:,2]
    lum_a = 0.299*a[:,:,0]+0.587*a[:,:,1]+0.114*a[:,:,2]
    diff = np.abs(lum_a - lum_b)
    combined = 0.55*cv2.GaussianBlur(diff,(21,21),0) + 0.45*cv2.GaussianBlur(diff,(5,5),0)
    mn,mx = combined.min(),combined.max()
    change_map = (combined-mn)/(mx-mn+1e-7)

    semantic = 0.5
    if clip:
        import torch, torch.nn.functional as F
        try:
            proc = clip["processor"]; model = clip["model"]
            bp = Image.fromarray(before_np); ap = Image.fromarray(after_np)
            inputs = proc(images=[bp,ap], return_tensors="pt", padding=True)
            with torch.no_grad():
                feats = model.get_image_features(pixel_values=inputs["pixel_values"])
            feats = F.normalize(feats, dim=-1)
            semantic = round(1.0 - float(torch.dot(feats[0],feats[1]).item()), 4)
        except Exception:
            pass

    hm = cv2.applyColorMap((change_map*255).astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.cvtColor(hm, cv2.COLOR_BGR2RGB), round(float(change_map.mean()*10), 2), semantic

def run_fusion(eo):
    gray = cv2.cvtColor(eo, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    ir = cv2.cvtColor(cv2.applyColorMap(clahe.apply(gray), cv2.COLORMAP_INFERNO), cv2.COLOR_BGR2RGB)
    noisy = np.clip(gray.astype(np.float32) + np.random.default_rng(42).rayleigh(7,(gray.shape)).astype(np.float32) - 3.5, 0, 255)
    sar = cv2.cvtColor(cv2.GaussianBlur(noisy,(5,5),0).astype(np.uint8), cv2.COLOR_GRAY2RGB)
    total = 0.5+0.3+0.2
    fused = np.clip(0.5*eo.astype(np.float32)+0.3*ir.astype(np.float32)+0.2*sar.astype(np.float32), 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(fused, cv2.COLOR_RGB2LAB)
    lab[:,:,0] = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8)).apply(lab[:,:,0])
    fused = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    return ir, sar, fused

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ SENTINELAI")
st.markdown("##### AI Battlefield Intelligence Platform · YOLOv8 · CLIP ViT-B/32 · EO/IR/SAR Fusion")
st.divider()

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ MISSION PARAMETERS")
    mode = st.selectbox("Analysis Module", [
        "🎯 Full Pipeline (Detect + Prioritize)",
        "🔍 Detect Assets Only",
        "🌡️ Modal Fusion (EO+IR+SAR)",
        "🔄 Change Detection",
    ])
    conf = st.slider("Confidence Threshold", 0.05, 0.95, 0.25, 0.05)
    mission = st.selectbox("Mission Context", ["general","anti_armor","sead","maritime"])
    st.divider()
    st.markdown("### 📍 SCENE BOUNDS")
    col1, col2 = st.columns(2)
    lat_min = col1.number_input("Lat Min", value=48.20, format="%.3f")
    lat_max = col2.number_input("Lat Max", value=48.40, format="%.3f")
    lon_min = col1.number_input("Lon Min", value=31.10, format="%.3f")
    lon_max = col2.number_input("Lon Max", value=31.30, format="%.3f")
    st.divider()
    st.caption("SentinelAI v1.0 · CPU Inference · YOLOv8n + CLIP ViT-B/32")

# Main area
is_change = "Change" in mode
if is_change:
    col1, col2 = st.columns(2)
    f1 = col1.file_uploader("📸 BEFORE (T1)", type=["jpg","jpeg","png","webp"])
    f2 = col2.file_uploader("📸 AFTER (T2)",  type=["jpg","jpeg","png","webp"])
    uploaded = f1 and f2
else:
    uploaded_file = st.file_uploader("📡 DROP SATELLITE / DRONE IMAGERY", type=["jpg","jpeg","png","webp","tif"])
    uploaded = uploaded_file is not None

if uploaded:
    run_btn = st.button("⚡ EXECUTE ANALYSIS", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner("🔄 Processing imagery through AI pipeline..."):
            t_start = time.perf_counter()

            if is_change:
                before_np = np.array(Image.open(f1).convert("RGB"))
                after_np  = np.array(Image.open(f2).convert("RGB").resize(
                    (before_np.shape[1], before_np.shape[0])))
                heatmap, pixel_score, semantic_score = run_change(before_np, after_np)
                total_ms = round((time.perf_counter()-t_start)*1000,1)

                st.success(f"Change analysis complete in {total_ms}ms")
                c1,c2,c3 = st.columns(3)
                c1.image(before_np, caption="BEFORE T1", use_container_width=True)
                c2.image(after_np,  caption="AFTER T2",  use_container_width=True)
                c3.image(heatmap,   caption="CHANGE MAP", use_container_width=True)

                st.markdown("### 📊 CHANGE METRICS")
                m1,m2,m3 = st.columns(3)
                m1.metric("Pixel Change Score", f"{pixel_score}/10")
                m2.metric("Semantic Distance (CLIP)", f"{semantic_score:.3f}")
                m3.metric("Processing Time", f"{total_ms}ms")

            elif "Fusion" in mode:
                img_np = np.array(Image.open(uploaded_file).convert("RGB"))
                ir, sar, fused = run_fusion(img_np)
                total_ms = round((time.perf_counter()-t_start)*1000,1)

                st.success(f"Fusion complete in {total_ms}ms")
                c1,c2,c3,c4 = st.columns(4)
                c1.image(img_np, caption="EO (Input)",    use_container_width=True)
                c2.image(ir,     caption="IR (Simulated)", use_container_width=True)
                c3.image(sar,    caption="SAR (Simulated)",use_container_width=True)
                c4.image(fused,  caption="FUSED OUTPUT",  use_container_width=True)
                st.info("Fusion: Channel-attention weighted blend (EO 50% · IR 30% · SAR 20%) + CLAHE contrast enhancement")

            else:
                img_np = np.array(Image.open(uploaded_file).convert("RGB"))
                assets, det_ms = run_detection(img_np, conf, mission)
                annotated = annotate(img_np, assets)
                total_ms = round((time.perf_counter()-t_start)*1000,1)

                # Threat counts
                counts = {l: sum(1 for a in assets if a["threat_level"]==l)
                          for l in ["critical","high","medium","low"]}

                st.success(f"Analysis complete — {len(assets)} assets detected in {total_ms}ms")

                # Metrics row
                m1,m2,m3,m4,m5 = st.columns(5)
                m1.metric("Total Assets", len(assets))
                m2.metric("🔴 Critical", counts["critical"])
                m3.metric("🟠 High",     counts["high"])
                m4.metric("🟡 Medium",   counts["medium"])
                m5.metric("⏱️ Latency",  f"{total_ms}ms")

                # Image + targets
                left, right = st.columns([2,1])
                with left:
                    st.markdown("#### 🖼️ ANNOTATED IMAGERY")
                    st.image(annotated, use_container_width=True)

                with right:
                    st.markdown("#### 🎯 PRIORITIZED TARGETS")
                    if not assets:
                        st.info("No assets detected. Try lowering the confidence threshold.")
                    for a in assets[:12]:
                        lv = a["threat_level"]
                        color = LEVEL_COLORS[lv]
                        st.markdown(f"""
                        <div class="target-card" style="border-left-color:{color}">
                            <div class="hud-header">{a['asset_id']} · {lv.upper()}</div>
                            <div style="color:{color};font-family:Orbitron,monospace;font-size:0.9rem;font-weight:900">
                                {a['military_class'].replace('_',' ').upper()}
                            </div>
                            <div style="color:#4a7090;font-size:0.65rem;margin-top:4px">
                                Score: <span style="color:{color}">{a['threat_score']:.1f}/10</span> &nbsp;·&nbsp;
                                Conf: <span style="color:#00aa55">{a['confidence']*100:.0f}%</span>
                            </div>
                            <div style="color:#ff6b00;font-size:0.6rem;margin-top:6px">▶ {a['action']}</div>
                        </div>
                        """, unsafe_allow_html=True)

else:
    st.info("👆 Upload a satellite or drone image in the panel above to begin analysis")
    st.markdown("""
    **Try uploading:**
    - Any aerial/satellite photo
    - Photos with vehicles, aircraft, boats, or people
    - Before/after images for change detection

    **What SentinelAI does:**
    - Detects objects and maps them to military asset classes
    - Scores each target by threat level (0–10)
    - Recommends tactical actions per target
    - Fuses EO + simulated IR + SAR imagery
    - Detects scene changes using CLIP ViT-B/32
    """)
