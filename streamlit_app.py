"""
SentinelAI — Streamlit Cloud Demo
Lightweight version: YOLOv8 detection only (no PyTorch/CLIP dependency)
"""
import io
import time
import numpy as np
import streamlit as st
from PIL import Image
import cv2

st.set_page_config(
    page_title="SentinelAI — Battlefield Intelligence",
    page_icon="🛡️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=IBM+Plex+Mono&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Mono', monospace; background: #020507; }
h1,h2,h3 { font-family: 'Orbitron', monospace !important; color: #00ff88 !important; }
.stApp { background: #020507; }
.target-card {
    background: rgba(6,13,20,0.9);
    border: 1px solid #0e2233;
    border-left: 3px solid #00ff88;
    border-radius: 3px;
    padding: 12px;
    margin-bottom: 8px;
    font-size: 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
}
</style>
""", unsafe_allow_html=True)

# ── Taxonomy ──────────────────────────────────────────────────────────────────
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
    "missile_launcher": "🔴 IMMEDIATE STRIKE — Time-critical target",
    "radar_array":      "🔴 PRIORITY STRIKE — Degrade C2 network",
    "c2_node":          "🔴 PRIORITY STRIKE — Disrupt command chain",
    "fighter_aircraft": "🟠 AIR INTERCEPT — Coordinate CAP",
    "command_vehicle":  "🟠 HIGH PRIORITY — Sever adversary coordination",
    "warship":          "🟠 MARITIME STRIKE — Coordinate naval assets",
    "armored_vehicle":  "🟡 ANTI-ARMOR TASKING — Brigade coordination",
}

LEVEL_COLORS = {
    "critical": "#ff1a1a",
    "high":     "#ff6b00",
    "medium":   "#ffd700",
    "low":      "#00ff88",
}

def threat_level(score):
    if score >= 8.5: return "critical"
    if score >= 6.5: return "high"
    if score >= 4.0: return "medium"
    return "low"

@st.cache_resource(show_spinner="⚙️ Loading YOLOv8 model...")
def load_detector():
    from ultralytics import YOLO
    return YOLO("yolov8n.pt")

def run_detection(img_np, conf, mission):
    detector = load_detector()
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
            r.boxes.cls.cpu().numpy().astype(int),
        )):
            x1, y1, x2, y2 = box.tolist()
            raw = r.names[cls_id]
            mil_cls, base = ASSET_TAXONOMY.get(raw, ("unidentified_asset", 4.0))
            score = min(10.0, base * (0.65 + 0.35 * float(cf)) * mults.get(mil_cls, 1.0))
            assets.append({
                "asset_id":       f"TGT-{i+1:03d}",
                "raw_class":      raw,
                "military_class": mil_cls,
                "confidence":     round(float(cf), 3),
                "threat_score":   round(score, 2),
                "threat_level":   threat_level(score),
                "bbox":           [x1, y1, x2, y2],
                "action":         ACTIONS.get(mil_cls, "🟢 CONTINUE ISR — Monitor and track"),
            })
    assets.sort(key=lambda a: a["threat_score"], reverse=True)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    return assets, ms

def annotate(img_np, assets):
    vis = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    colors = {
        "critical": (30,30,220),
        "high":     (30,120,230),
        "medium":   (30,200,220),
        "low":      (30,200,80),
    }
    for a in assets:
        x1,y1,x2,y2 = [int(v) for v in a["bbox"]]
        c = colors[a["threat_level"]]
        cv2.rectangle(vis, (x1,y1), (x2,y2), c, 2)
        sz = max(6, min(14, (x2-x1)//6))
        for px,py,dx,dy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
            cv2.line(vis,(px,py),(px+dx*sz,py),c,2)
            cv2.line(vis,(px,py),(px,py+dy*sz),c,2)
        lbl = f"{a['asset_id']} {a['military_class'].replace('_',' ').upper()} {a['threat_score']:.1f}"
        (tw,th),_ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        cv2.rectangle(vis,(x1,y1-th-6),(x1+tw+6,y1),c,-1)
        cv2.putText(vis,lbl,(x1+3,y1-3),cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,0,0),1,cv2.LINE_AA)
    counts = {l: sum(1 for a in assets if a["threat_level"]==l)
              for l in ["critical","high","medium","low"]}
    hud = (f"ASSETS:{len(assets)}  CRITICAL:{counts['critical']}  "
           f"HIGH:{counts['high']}  MED:{counts['medium']}  LOW:{counts['low']}")
    cv2.rectangle(vis,(0,0),(vis.shape[1],26),(0,0,0),-1)
    cv2.putText(vis,hud,(8,17),cv2.FONT_HERSHEY_SIMPLEX,0.52,(0,220,180),1,cv2.LINE_AA)
    return cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)

def run_fusion(eo):
    gray = cv2.cvtColor(eo, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    ir = cv2.cvtColor(
        cv2.applyColorMap(clahe.apply(gray), cv2.COLORMAP_INFERNO),
        cv2.COLOR_BGR2RGB)
    rng = np.random.default_rng(42)
    noisy = np.clip(
        gray.astype(np.float32) + rng.rayleigh(7, gray.shape).astype(np.float32) - 3.5,
        0, 255)
    sar = cv2.cvtColor(
        cv2.GaussianBlur(noisy,(5,5),0).astype(np.uint8),
        cv2.COLOR_GRAY2RGB)
    blended = np.clip(
        0.5*eo.astype(np.float32) +
        0.3*ir.astype(np.float32) +
        0.2*sar.astype(np.float32), 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(blended, cv2.COLOR_RGB2LAB)
    lab[:,:,0] = cv2.createCLAHE(clipLimit=2.5,tileGridSize=(8,8)).apply(lab[:,:,0])
    return ir, sar, cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

def run_change(before_np, after_np):
    b = before_np.astype(np.float32)
    a = after_np.astype(np.float32)
    lum_b = 0.299*b[:,:,0]+0.587*b[:,:,1]+0.114*b[:,:,2]
    lum_a = 0.299*a[:,:,0]+0.587*a[:,:,1]+0.114*a[:,:,2]
    diff = np.abs(lum_a - lum_b)
    combined = (0.55*cv2.GaussianBlur(diff,(21,21),0) +
                0.45*cv2.GaussianBlur(diff,(5,5),0))
    mn, mx = combined.min(), combined.max()
    change_map = (combined - mn) / (mx - mn + 1e-7)
    hm = cv2.applyColorMap((change_map*255).astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.cvtColor(hm, cv2.COLOR_BGR2RGB), round(float(change_map.mean()*10), 2)

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ SENTINELAI")
st.markdown("##### AI Battlefield Intelligence Platform · YOLOv8 · EO/IR/SAR Fusion · Multi-Factor Threat Scoring")
st.divider()

with st.sidebar:
    st.markdown("### ⚙️ MISSION PARAMETERS")
    mode = st.selectbox("Analysis Module", [
        "🎯 Full Pipeline (Detect + Prioritize)",
        "🌡️ Modal Fusion (EO+IR+SAR)",
        "🔄 Change Detection",
    ])
    conf    = st.slider("Confidence Threshold", 0.05, 0.95, 0.25, 0.05)
    mission = st.selectbox("Mission Context", ["general","anti_armor","sead","maritime"])
    st.divider()
    st.caption("SentinelAI v1.0 · YOLOv8n · CPU Inference")
    st.caption("github.com/tusharg007/sentinelai")

is_change = "Change" in mode

if is_change:
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("📸 BEFORE (T1)", type=["jpg","jpeg","png","webp"])
    f2 = c2.file_uploader("📸 AFTER (T2)",  type=["jpg","jpeg","png","webp"])
    ready = f1 and f2
else:
    uploaded_file = st.file_uploader(
        "📡 DROP SATELLITE / DRONE / AERIAL IMAGERY",
        type=["jpg","jpeg","png","webp"],
        help="Upload any image with vehicles, aircraft, boats, or people")
    ready = uploaded_file is not None

if ready:
    if st.button("⚡ EXECUTE ANALYSIS", type="primary", use_container_width=True):
        with st.spinner("🔄 Processing through AI pipeline..."):
            t0 = time.perf_counter()

            if is_change:
                before_np = np.array(Image.open(f1).convert("RGB"))
                h, w = before_np.shape[:2]
                after_np  = np.array(Image.open(f2).convert("RGB").resize((w,h)))
                heatmap, score = run_change(before_np, after_np)
                ms = round((time.perf_counter()-t0)*1000,1)
                st.success(f"Change analysis complete in {ms}ms")
                ca,cb,cc = st.columns(3)
                ca.image(before_np, caption="BEFORE T1",  use_container_width=True)
                cb.image(after_np,  caption="AFTER T2",   use_container_width=True)
                cc.image(heatmap,   caption="CHANGE MAP", use_container_width=True)
                st.metric("Change Intensity Score", f"{score}/10")

            elif "Fusion" in mode:
                img_np = np.array(Image.open(uploaded_file).convert("RGB"))
                ir, sar, fused = run_fusion(img_np)
                ms = round((time.perf_counter()-t0)*1000,1)
                st.success(f"Fusion complete in {ms}ms")
                ca,cb,cc,cd = st.columns(4)
                ca.image(img_np, caption="EO INPUT",      use_container_width=True)
                cb.image(ir,     caption="IR SIMULATED",  use_container_width=True)
                cc.image(sar,    caption="SAR SIMULATED", use_container_width=True)
                cd.image(fused,  caption="FUSED OUTPUT",  use_container_width=True)
                st.info("Channel-attention fusion: EO 50% · IR 30% · SAR 20% · CLAHE contrast enhancement")

            else:
                img_np = np.array(Image.open(uploaded_file).convert("RGB"))
                assets, det_ms = run_detection(img_np, conf, mission)
                annotated = annotate(img_np, assets)
                ms = round((time.perf_counter()-t0)*1000,1)
                counts = {l: sum(1 for a in assets if a["threat_level"]==l)
                          for l in ["critical","high","medium","low"]}

                st.success(f"✅ {len(assets)} assets detected in {ms}ms")

                m1,m2,m3,m4,m5 = st.columns(5)
                m1.metric("Total Assets",  len(assets))
                m2.metric("🔴 Critical",   counts["critical"])
                m3.metric("🟠 High",       counts["high"])
                m4.metric("🟡 Medium",     counts["medium"])
                m5.metric("⏱️ Latency",    f"{ms}ms")

                left, right = st.columns([2,1])
                with left:
                    st.markdown("#### 🖼️ ANNOTATED IMAGERY")
                    st.image(annotated, use_container_width=True)
                with right:
                    st.markdown("#### 🎯 PRIORITIZED TARGETS")
                    if not assets:
                        st.info("No assets detected. Try lowering the confidence threshold or upload an image with vehicles/people/aircraft.")
                    for a in assets[:15]:
                        color = LEVEL_COLORS[a["threat_level"]]
                        st.markdown(f"""
                        <div class="target-card" style="border-left-color:{color}">
                            <span style="color:#3a6080;font-size:0.6rem">{a['asset_id']} · {a['threat_level'].upper()}</span><br>
                            <span style="color:{color};font-family:Orbitron,monospace;font-weight:900">
                                {a['military_class'].replace('_',' ').upper()}
                            </span><br>
                            <span style="color:#4a7090;font-size:0.65rem">
                                Score: <b style="color:{color}">{a['threat_score']:.1f}/10</b>
                                &nbsp;·&nbsp; Conf: <b style="color:#00aa55">{a['confidence']*100:.0f}%</b>
                            </span><br>
                            <span style="color:#ff6b00;font-size:0.6rem">{a['action']}</span>
                        </div>
                        """, unsafe_allow_html=True)
else:
    st.info("👆 Upload an image above to begin analysis")
    st.markdown("""
    **What SentinelAI detects:**
    Upload any photo containing vehicles, aircraft, boats, or people and SentinelAI will:
    - Map detected objects to **military asset classes** (tank, radar, aircraft, warship...)
    - Assign a **threat score 0–10** with priority label
    - Recommend a **tactical action** per target
    - Generate an **annotated intelligence image**

    **Best test images:** aerial/satellite photos, traffic scenes, airports, harbors, military imagery.
    """)
