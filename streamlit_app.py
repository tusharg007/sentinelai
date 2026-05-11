"""
SentinelAI — Streamlit Cloud Demo
Lightweight version: YOLOv8 detection only (no PyTorch/CLIP dependency)
Supports: Demo Mode, Upload Image, Upload Video, Live Camera (Webcam), RTSP Stream
"""
import io
import time
import numpy as np
import streamlit as st
from PIL import Image
import cv2
import tempfile
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

st.set_page_config(
    page_title="SentinelAI — Aerial Intelligence",
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
    "infrastructure": {"armored_vehicle": 1.4, "missile_launcher": 1.2},
    "disaster_response": {"radar_array": 1.5, "c2_node": 1.4, "fighter_aircraft": 1.2},
    "urban_planning": {"warship": 1.4, "radar_array": 1.1},
}

ACTIONS = {
    "missile_launcher": "🔴 HIGH PRIORITY ALERT — Time-critical target",
    "radar_array":      "🔴 HIGH PRIORITY ALERT — Monitor critical cluster",
    "c2_node":          "🔴 HIGH PRIORITY ALERT — Investigate high-value asset",
    "fighter_aircraft": "🟠 PRIORITY RECOMMENDATION — Aerial anomaly",
    "command_vehicle":  "🟠 HIGH PRIORITY ALERT — Fleet coordination needed",
    "warship":          "🟠 MARITIME PRIORITY — Coastal monitoring",
    "armored_vehicle":  "🟡 HEAVY ASSET TRACKING — Monitor movements",
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
                "action":         ACTIONS.get(mil_cls, "🟢 CONTINUE MONITORING — Standard observation"),
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

def capture_video_thread(source, stop_event, frame_container):
    """Run cv2.VideoCapture in a separate thread to avoid blocking Streamlit's main thread."""
    try:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            frame_container["error"] = f"Failed to open video source: {source}"
            return
        frame_container["error"] = None
        while cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                if isinstance(source, str) and source.startswith("rtsp"):
                    # RTSP streams can temporarily fail — retry
                    time.sleep(0.5)
                    continue
                break
            frame_container["frame"] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            time.sleep(0.01)
        cap.release()
    except Exception as e:
        frame_container["error"] = str(e)

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ SENTINELAI")
st.markdown("##### AI Aerial Intelligence Platform · YOLOv8 · EO/IR/SAR Fusion · Multi-Factor Threat Scoring")
st.divider()

with st.sidebar:
    st.markdown("### 📡 INPUT SOURCE")
    input_source = st.radio("Select Source", [
        "Demo Mode",
        "Upload Image",
        "Upload Video",
        "Live Camera (Webcam)",
        "RTSP Stream"
    ])
    
    rtsp_url = ""
    if input_source == "RTSP Stream":
        rtsp_url = st.text_input("RTSP URL", "rtsp://...")
        
    uploaded_video = None
    if input_source == "Upload Video":
        uploaded_video = st.file_uploader("Upload Video", type=["mp4", "avi", "mov"])
        
    st.markdown("### ⚙️ PARAMETERS")
    mode = st.selectbox("Analysis Module", [
        "🎯 Full Pipeline (Detect + Prioritize)",
        "🌡️ Modal Fusion (EO+IR+SAR)",
        "🔄 Change Detection",
    ])
    conf = st.slider("Confidence Threshold", 0.05, 0.95, 0.25, 0.05)
    mission = st.selectbox("Context Profile", ["general", "infrastructure", "disaster_response", "urban_planning"])
    st.divider()
    st.caption("SentinelAI v1.0 · YOLOv8n · CPU Inference")
    st.caption("github.com/tusharg007/sentinelai")

is_change = "Change" in mode
is_live = input_source in ["Upload Video", "Live Camera (Webcam)", "RTSP Stream"]

# ── Session state for stream control ──────────────────────────────────────────
if 'stop_stream' not in st.session_state:
    st.session_state.stop_stream = False
if 'take_snapshot' not in st.session_state:
    st.session_state.take_snapshot = False
if 'last_annotated_frame' not in st.session_state:
    st.session_state.last_annotated_frame = None

# ── Determine readiness ──────────────────────────────────────────────────────
if is_change:
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("📸 BEFORE (T1)", type=["jpg","jpeg","png","webp"])
    f2 = c2.file_uploader("📸 AFTER (T2)",  type=["jpg","jpeg","png","webp"])
    ready = f1 and f2
elif input_source == "Upload Image":
    uploaded_file = st.file_uploader("📡 DROP AERIAL IMAGERY", type=["jpg","jpeg","png","webp"])
    ready = uploaded_file is not None
elif is_live:
    if input_source == "Upload Video":
        ready = uploaded_video is not None
    elif input_source == "RTSP Stream":
        ready = rtsp_url != "" and rtsp_url != "rtsp://..."
    else:
        ready = True
else:
    # Demo Mode
    ready = True

# ── Static analysis modes (Demo, Upload Image, Change Detection, Fusion) ─────
if ready and not is_live:
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
                # Use a dummy if demo
                if input_source == "Demo Mode":
                    img_np = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
                else:
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
                if input_source == "Demo Mode":
                    img_np = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
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
                        st.info("No assets detected.")
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

# ── Live / Video streaming modes ──────────────────────────────────────────────
elif is_live and ready:
    st.markdown("#### 📹 LIVE STREAM")

    # Stream control buttons
    col_stop, col_snap = st.columns(2)
    with col_stop:
        if st.button("🛑 Stop Stream", use_container_width=True, key="btn_stop_stream"):
            st.session_state.stop_stream = True
    with col_snap:
        if st.button("📸 Snapshot", use_container_width=True, key="btn_snapshot"):
            st.session_state.take_snapshot = True

    if not st.session_state.stop_stream:
        st_frame = st.empty()
        st_hud = st.empty()
        st_snapshot_area = st.empty()

        # Determine video source
        source = 0  # default: webcam
        if input_source == "Upload Video":
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded_video.read())
            tfile.flush()
            source = tfile.name
        elif input_source == "RTSP Stream":
            source = rtsp_url

        # Launch capture in a separate thread
        stop_event = threading.Event()
        frame_container = {"frame": None, "error": None}
        t = threading.Thread(
            target=capture_video_thread,
            args=(source, stop_event, frame_container),
            daemon=True,
        )
        add_script_run_ctx(t)
        t.start()

        # Wait briefly for the thread to start capturing
        time.sleep(0.5)

        # Check for connection errors
        if frame_container.get("error"):
            st.error(f"⚠️ Connection failed: {frame_container['error']}")
            st.info("Please check the video source and try again. For webcam, ensure no other application is using it.")
            stop_event.set()
        else:
            frame_count = 0
            while not st.session_state.stop_stream:
                if frame_container["frame"] is not None:
                    img_np = frame_container["frame"].copy()

                    t_inf = time.perf_counter()
                    assets, det_ms = run_detection(img_np, conf, mission)
                    annotated = annotate(img_np, assets)
                    fps = 1.0 / (time.perf_counter() - t_inf + 1e-5)

                    counts = {l: sum(1 for a in assets if a["threat_level"]==l)
                              for l in ["critical","high","medium","low"]}
                    top_score = max([a["threat_score"] for a in assets]) if assets else 0.0

                    st_frame.image(annotated, use_container_width=True)

                    st_hud.markdown(
                        f"**Live Metrics** | FPS: `{fps:.1f}` | "
                        f"Detected Objects: `{len(assets)}` | "
                        f"Highest Threat Score: `{top_score:.1f}` | "
                        f"🔴 Critical: `{counts['critical']}` | "
                        f"🟠 High: `{counts['high']}`"
                    )

                    # Store last annotated frame for snapshot
                    st.session_state.last_annotated_frame = annotated

                    # Handle snapshot request
                    if st.session_state.take_snapshot:
                        img_bytes = io.BytesIO()
                        Image.fromarray(annotated).save(img_bytes, format="JPEG")
                        st_snapshot_area.download_button(
                            label="⬇️ Download Snapshot",
                            data=img_bytes.getvalue(),
                            file_name=f"sentinelai_snapshot_{int(time.time())}.jpg",
                            mime="image/jpeg",
                        )
                        st.session_state.take_snapshot = False

                    frame_count += 1
                else:
                    # Check if thread reported an error after starting
                    if frame_container.get("error"):
                        st.error(f"⚠️ Stream error: {frame_container['error']}")
                        break

                time.sleep(0.05)

            # Clean up
            stop_event.set()
            t.join(timeout=3)
            st.info("Stream stopped.")
    else:
        st.info("Stream stopped. Change source or refresh to restart.")
        # Reset stop state for next run
        st.session_state.stop_stream = False

else:
    if not ready:
        st.info("👆 Upload an image/video or select a source above to begin analysis")
    st.markdown("""
    **What SentinelAI detects:**
    Upload any photo/video containing high-value assets and SentinelAI will:
    - Map detected objects to **high-value asset classes** (heavy machinery, radar, aircraft, ships...)
    - Assign a **threat score 0–10** with priority label
    - Recommend an **automated priority recommendation** per target
    - Generate an **annotated intelligence image**

    **Best test images:** aerial/satellite photos, traffic scenes, airports, harbors, infrastructure survey imagery.
    """)
