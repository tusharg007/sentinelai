import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { Crosshair, Layers, RefreshCw, Zap, UploadCloud, AlertTriangle } from 'lucide-react'
import api from '@/lib/api'
import type { AnalysisMode, MissionContext, DetectedAsset, ThreatCounts, PipelineResult, DetectionResult } from '@/lib/types'
import ThreatSummaryCard from '@/components/ui/ThreatSummaryCard'
import TargetCard from '@/components/ui/TargetCard'

const MODES: { id: AnalysisMode; label: string; icon: React.ReactNode; desc: string }[] = [
  { id: 'pipeline', label: 'FULL PIPELINE', icon: <Zap size={13} />,       desc: 'Detect · Geolocate · Prioritize' },
  { id: 'detect',   label: 'DETECT ASSETS', icon: <Crosshair size={13} />, desc: 'YOLOv8 military asset detection' },
  { id: 'fuse',     label: 'MODAL FUSION',  icon: <Layers size={13} />,    desc: 'EO + IR + SAR fusion' },
  { id: 'change',   label: 'CHANGE DETECT', icon: <RefreshCw size={13} />, desc: 'Temporal change between passes' },
]

const CONTEXTS: { id: MissionContext; label: string }[] = [
  { id: 'general',    label: 'GENERAL RECON' },
  { id: 'anti_armor', label: 'ANTI-ARMOR OPS' },
  { id: 'sead',       label: 'SEAD MISSION' },
  { id: 'maritime',   label: 'MARITIME STRIKE' },
]

const EMPTY_COUNTS: ThreatCounts = { critical: 0, high: 0, medium: 0, low: 0 }

export default function AnalysisPage() {
  const [mode, setMode]         = useState<AnalysisMode>('pipeline')
  const [file, setFile]         = useState<File | null>(null)
  const [preview, setPreview]   = useState<string | null>(null)
  const [conf, setConf]         = useState(0.25)
  const [mission, setMission]   = useState<MissionContext>('general')
  const [latMin, setLatMin]     = useState(48.2)
  const [latMax, setLatMax]     = useState(48.4)
  const [lonMin, setLonMin]     = useState(31.1)
  const [lonMax, setLonMax]     = useState(31.3)
  const [gsd, setGsd]           = useState(0.5)
  const [resultImg, setResultImg] = useState<string | null>(null)
  const [assets, setAssets]       = useState<DetectedAsset[]>([])
  const [counts, setCounts]       = useState<ThreatCounts>(EMPTY_COUNTS)
  const [summary, setSummary]     = useState<PipelineResult['mission_summary'] | null>(null)
  const [latency, setLatency]     = useState<number | null>(null)

  const onDrop = useCallback((files: File[]) => {
    const f = files[0]; if (!f) return
    setFile(f); setResultImg(null); setAssets([]); setCounts(EMPTY_COUNTS); setSummary(null)
    setPreview(URL.createObjectURL(f))
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'image/*': ['.jpg','.jpeg','.png','.tif','.tiff','.webp'] }, maxFiles: 1,
  })

  const run = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No image selected')
      const fd = new FormData()
      fd.append('confidence', String(conf))
      fd.append('lat_min', String(latMin)); fd.append('lat_max', String(latMax))
      fd.append('lon_min', String(lonMin)); fd.append('lon_max', String(lonMax))
      fd.append('gsd_m', String(gsd))
      fd.append('mission', mission)

      if (mode === 'pipeline') {
        fd.append('file', file)
        return api.post<PipelineResult>('/pipeline/', fd).then(r => r.data)
      } else if (mode === 'detect') {
        fd.append('file', file)
        fd.append('annotate', 'true')
        return api.post<DetectionResult>('/detect/', fd).then(r => r.data)
      } else if (mode === 'fuse') {
        fd.append('eo_file', file)
        return api.post('/fuse/', fd).then(r => r.data)
      } else {
        fd.append('before', file); fd.append('after', file)
        fd.append('sensitivity', String(conf))
        return api.post('/change/', fd).then(r => r.data)
      }
    },
    onSuccess: (data: any) => {
      // Extract assets & counts from different response shapes
      let a: DetectedAsset[] = []
      let c: ThreatCounts = EMPTY_COUNTS
      let img: string | null = null

      if (mode === 'pipeline') {
        const r = data as PipelineResult
        a = r.top_targets ?? []
        c = r.detection?.threat_counts ?? EMPTY_COUNTS
        img = r.detection?.annotated_b64 ? `data:image/jpeg;base64,${r.detection.annotated_b64}` : null
        setSummary(r.mission_summary)
        setLatency(r.latency_ms)
      } else if (mode === 'detect') {
        const r = data as DetectionResult
        a = r.assets ?? []
        c = r.threat_counts ?? EMPTY_COUNTS
        img = r.annotated_b64 ? `data:image/jpeg;base64,${r.annotated_b64}` : null
        setLatency(r.latency_ms)
      } else if (mode === 'fuse') {
        a = (data.detections ?? []).map((d: any, i: number) => ({
          asset_id: `TGT-${i+1}`, raw_class: d.asset, military_class: d.asset,
          confidence: d.confidence, threat_score: d.threat_score, threat_level: d.threat_score >= 8.5 ? 'critical' : d.threat_score >= 6.5 ? 'high' : d.threat_score >= 4 ? 'medium' : 'low',
          bbox: { x1:0,y1:0,x2:0,y2:0,x1n:0,y1n:0,x2n:0,y2n:0 }, area_fraction: 0,
        }))
        img = data.strip_b64 ? `data:image/jpeg;base64,${data.strip_b64}` : null
        setLatency(data.latency_ms)
      } else {
        img = data.strip_b64 ? `data:image/jpeg;base64,${data.strip_b64}` : null
        setLatency(data.latency_ms)
      }
      setAssets(a); setCounts(c); setResultImg(img)
      toast.success('Analysis complete')
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? err.message ?? 'Analysis failed'),
  })

  return (
    <div className="h-full flex relative z-10">
      {/* ── Left: Controls ──────────────────────────────────────────── */}
      <div className="w-[272px] flex flex-col overflow-y-auto shrink-0 border-r" style={{ borderColor: 'var(--border)', background: 'rgba(6,13,20,0.7)' }}>

        {/* Mode */}
        <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="section-header font-hud text-[0.57rem] tracking-widest uppercase mb-3" style={{ color: 'var(--accent)' }}>Analysis Module</div>
          <div className="grid grid-cols-2 gap-1.5">
            {MODES.map(m => (
              <button key={m.id} onClick={() => setMode(m.id)}
                className="p-2.5 text-left rounded border transition-all cursor-pointer"
                style={{ background: mode===m.id ? 'rgba(0,255,136,0.06)' : 'rgba(0,0,0,0.3)', borderColor: mode===m.id ? 'var(--accent)' : 'var(--border)', color: mode===m.id ? 'var(--accent)' : 'var(--text-dim)' }}>
                <div className="flex items-center gap-1.5 mb-1">{m.icon}<span className="font-hud text-[0.53rem] tracking-wider">{m.label}</span></div>
                <div className="font-mono text-[0.53rem]" style={{ color: 'var(--muted)' }}>{m.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Upload */}
        <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="section-header font-hud text-[0.57rem] tracking-widest uppercase mb-3" style={{ color: 'var(--accent)' }}>Imagery Input</div>
          <div {...getRootProps()} className="rounded border-2 border-dashed cursor-pointer transition-all overflow-hidden"
            style={{ borderColor: isDragActive ? 'var(--accent)' : file ? 'var(--accent-dim)' : 'var(--border)', background: isDragActive ? 'rgba(0,255,136,0.04)' : 'rgba(0,0,0,0.3)', minHeight: file ? 'auto' : 90 }}>
            <input {...getInputProps()} />
            {file
              ? <img src={preview!} alt="Preview" className="w-full max-h-40 object-contain" />
              : <div className="flex flex-col items-center justify-center h-20 gap-2">
                  <UploadCloud size={20} style={{ color: 'var(--text-dim)' }} />
                  <span className="font-mono text-[0.6rem]" style={{ color: 'var(--text-dim)' }}>DROP EO · IR · SAR · GeoTIFF</span>
                </div>
            }
          </div>
          {file && <div className="mt-1 font-mono text-[0.58rem]" style={{ color: 'var(--muted)' }}>{file.name} ({(file.size/1024).toFixed(0)}KB)</div>}
        </div>

        {/* Params */}
        <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="section-header font-hud text-[0.57rem] tracking-widest uppercase mb-3" style={{ color: 'var(--accent)' }}>Mission Parameters</div>
          <div className="space-y-2.5">
            <label className="block">
              <div className="font-hud text-[0.53rem] tracking-wider uppercase mb-1" style={{ color: 'var(--muted)' }}>Confidence Threshold</div>
              <input type="number" value={conf} onChange={e => setConf(+e.target.value)} step={0.05} min={0.05} max={0.95} className="tac-input text-sm" />
            </label>
            <label className="block">
              <div className="font-hud text-[0.53rem] tracking-wider uppercase mb-1" style={{ color: 'var(--muted)' }}>Mission Context</div>
              <select value={mission} onChange={e => setMission(e.target.value as MissionContext)} className="tac-input text-sm" style={{ color: 'var(--text-primary)' }}>
                {CONTEXTS.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
              </select>
            </label>
            <div>
              <div className="font-hud text-[0.53rem] tracking-wider uppercase mb-1" style={{ color: 'var(--muted)' }}>Lat Bounds</div>
              <div className="grid grid-cols-2 gap-1.5">
                <input type="number" value={latMin} onChange={e => setLatMin(+e.target.value)} step={0.001} className="tac-input text-xs" placeholder="min" />
                <input type="number" value={latMax} onChange={e => setLatMax(+e.target.value)} step={0.001} className="tac-input text-xs" placeholder="max" />
              </div>
            </div>
            <div>
              <div className="font-hud text-[0.53rem] tracking-wider uppercase mb-1" style={{ color: 'var(--muted)' }}>Lon Bounds</div>
              <div className="grid grid-cols-2 gap-1.5">
                <input type="number" value={lonMin} onChange={e => setLonMin(+e.target.value)} step={0.001} className="tac-input text-xs" placeholder="min" />
                <input type="number" value={lonMax} onChange={e => setLonMax(+e.target.value)} step={0.001} className="tac-input text-xs" placeholder="max" />
              </div>
            </div>
            <label className="block">
              <div className="font-hud text-[0.53rem] tracking-wider uppercase mb-1" style={{ color: 'var(--muted)' }}>GSD (m/px)</div>
              <input type="number" value={gsd} onChange={e => setGsd(+e.target.value)} step={0.1} min={0.05} className="tac-input text-sm" />
            </label>
          </div>
        </div>

        {/* Execute */}
        <div className="p-4">
          <button className={`tac-btn w-full ${run.isPending ? 'running' : ''}`}
            onClick={() => run.mutate()} disabled={run.isPending || !file}>
            {run.isPending ? '◌ ANALYZING...' : '◈ EXECUTE ANALYSIS'}
          </button>
          {latency !== null && (
            <div className="mt-2 text-center font-mono text-[0.58rem]" style={{ color: 'var(--muted)' }}>
              Processed in {latency.toFixed(0)}ms
            </div>
          )}
        </div>
      </div>

      {/* ── Center: Tactical Display ─────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 relative overflow-hidden flex items-center justify-center" style={{ background: 'rgba(2,5,7,0.6)' }}>
          {/* Corner brackets */}
          {(['top-2.5 left-2.5 border-t border-l','top-2.5 right-2.5 border-t border-r','bottom-2.5 left-2.5 border-b border-l','bottom-2.5 right-2.5 border-b border-r'] as const).map((cls, i) => (
            <div key={i} className={`absolute w-4 h-4 ${cls}`} style={{ borderColor: 'rgba(0,255,136,0.2)' }} />
          ))}
          {/* Crosshair */}
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-1/2 left-0 right-0 h-px" style={{ background: 'rgba(0,255,136,0.04)' }} />
            <div className="absolute left-1/2 top-0 bottom-0 w-px" style={{ background: 'rgba(0,255,136,0.04)' }} />
          </div>

          <AnimatePresence mode="wait">
            {resultImg ? (
              <motion.img key="result" src={resultImg} alt="Analysis result"
                className="max-w-full max-h-full object-contain"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }} />
            ) : preview ? (
              <motion.img key="preview" src={preview} alt="Input"
                className="max-w-full max-h-full object-contain opacity-50"
                initial={{ opacity: 0 }} animate={{ opacity: 0.5 }} />
            ) : (
              <motion.div key="empty" className="flex flex-col items-center gap-4"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="relative w-20 h-20">
                  <div className="absolute inset-0 rounded-full border" style={{ borderColor: 'rgba(0,255,136,0.18)' }} />
                  <div className="absolute inset-3 rounded-full border" style={{ borderColor: 'rgba(0,255,136,0.1)' }} />
                  <div className="absolute top-1/2 left-1/2 w-1/2 h-px origin-left radar-sweep"
                    style={{ background: 'linear-gradient(90deg, transparent, var(--accent))' }} />
                </div>
                <div className="font-mono text-[0.68rem]" style={{ color: 'var(--text-dim)' }}>AWAITING IMAGERY INPUT</div>
                <div className="font-mono text-[0.6rem]" style={{ color: 'var(--muted)' }}>Upload satellite or drone imagery to begin</div>
              </motion.div>
            )}
          </AnimatePresence>

          {run.isPending && (
            <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'rgba(2,5,7,0.65)' }}>
              <div className="text-center">
                <div className="font-hud text-[0.7rem] tracking-widest mb-2" style={{ color: 'var(--warn)', animation: 'pulseWarn 1s ease infinite' }}>
                  ◈ PROCESSING IMAGERY...
                </div>
                <div className="w-48 h-0.5 overflow-hidden rounded mx-auto" style={{ background: 'rgba(255,107,0,0.2)' }}>
                  <div className="h-full w-1/2 animate-pulse" style={{ background: 'var(--warn)' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Status bar */}
        <div className="h-9 border-t flex items-center px-4 gap-6 shrink-0"
          style={{ borderColor: 'var(--border)', background: 'rgba(6,13,20,0.9)' }}>
          {[
            ['STATUS', run.isPending ? 'PROCESSING' : assets.length > 0 ? 'COMPLETE' : 'STANDBY', run.isPending ? 'var(--warn)' : assets.length > 0 ? 'var(--accent)' : 'var(--text-dim)'],
            ['ASSETS', String(assets.length || '--'), 'var(--text-primary)'],
            ['MODE',   mode.toUpperCase(), 'var(--text-dim)'],
            ['LATENCY', latency ? `${latency.toFixed(0)}ms` : '--', 'var(--text-dim)'],
          ].map(([k, v, c]) => (
            <div key={k} className="flex items-center gap-2 font-mono text-[0.6rem]">
              <span style={{ color: 'var(--muted)' }}>{k}</span>
              <span style={{ color: c }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right: Intel Panel ───────────────────────────────────── */}
      <div className="w-[292px] flex flex-col overflow-hidden border-l shrink-0"
        style={{ borderColor: 'var(--border)', background: 'rgba(6,13,20,0.7)' }}>

        <div className="p-3 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="section-header font-hud text-[0.54rem] tracking-widest uppercase mb-2" style={{ color: 'var(--accent)' }}>Threat Summary</div>
          <ThreatSummaryCard counts={counts} compact />
        </div>

        {summary && (
          <div className="p-3 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="section-header font-hud text-[0.54rem] tracking-widest uppercase mb-2" style={{ color: 'var(--accent)' }}>Mission Summary</div>
            <div className="space-y-1.5 font-mono text-[0.61rem]">
              {[
                ['TOP THREAT',   summary.top_asset],
                ['SCORE',        `${summary.top_score}/10`],
                ['TOTAL ASSETS', String(summary.total_assets)],
                ['GSD',          `${summary.gsd_m}m/px`],
                ['CENTER LAT',   String(summary.scene_center.lat)],
                ['CENTER LON',   String(summary.scene_center.lon)],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span style={{ color: 'var(--muted)' }}>{k}</span>
                  <span style={{ color: 'var(--text-primary)' }}>{v}</span>
                </div>
              ))}
              <div className="pt-1.5 mt-1 text-[0.57rem]" style={{ borderTop: '1px solid var(--border)', color: 'var(--warn)' }}>
                ▶ {summary.action}
              </div>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-3">
          <div className="section-header font-hud text-[0.54rem] tracking-widest uppercase mb-2" style={{ color: 'var(--accent)' }}>
            Targets ({assets.length})
          </div>
          {assets.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 gap-2">
              <AlertTriangle size={18} style={{ color: 'var(--muted)' }} />
              <div className="font-mono text-[0.63rem] text-center" style={{ color: 'var(--muted)' }}>
                {run.isPending ? 'Processing...' : 'No targets detected'}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {assets.slice(0, 20).map((a, i) => <TargetCard key={a.asset_id} asset={a} index={i} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
