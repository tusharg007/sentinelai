// ── Auth ──────────────────────────────────────────────────────────────────────
export interface User {
  id: string
  email: string
  full_name: string
  role: string
  clearance_level: string
  created_at: string
}

// ── Detection ─────────────────────────────────────────────────────────────────
export interface BoundingBox {
  x1: number; y1: number; x2: number; y2: number
  x1n: number; y1n: number; x2n: number; y2n: number
}

export interface DetectedAsset {
  asset_id: string
  raw_class: string
  military_class: string
  confidence: number
  threat_score: number
  threat_level: 'critical' | 'high' | 'medium' | 'low'
  bbox: BoundingBox
  area_fraction: number
  // Added by geolocation step
  lat?: number | null
  lon?: number | null
  coord_str?: string | null
  mgrs?: string | null
  footprint_m2?: number | null
  // Added by prioritization step
  final_score?: number
  priority_label?: string
  action?: string
  rank?: number
}

export interface ThreatCounts {
  critical: number
  high: number
  medium: number
  low: number
}

export interface DetectionResult {
  assets: DetectedAsset[]
  total: number
  threat_counts: ThreatCounts
  top_threat: string | null
  annotated_b64: string | null
  latency_ms: number
  image_wh: [number, number]
}

// ── Fusion ────────────────────────────────────────────────────────────────────
export interface FusionResult {
  detections: DetectedAsset[]
  total: number
  modalities: string[]
  fusion_method: string
  confidence_gain_pct: number
  strip_b64: string | null
  latency_ms: number
}

// ── Change detection ──────────────────────────────────────────────────────────
export interface ChangeRegion {
  region_id: string
  change_type: string
  magnitude: number
  bbox: [number, number, number, number]
  area_fraction: number
  significance: string
}

export interface ChangeResult {
  regions: ChangeRegion[]
  total: number
  global_score: number
  type_counts: Record<string, number>
  heatmap_b64: string | null
  strip_b64: string | null
  latency_ms: number
}

// ── Pipeline ──────────────────────────────────────────────────────────────────
export interface MissionSummary {
  total_assets: number
  threat_counts: ThreatCounts
  top_asset: string
  top_score: number
  action: string
  mission: string
  scene_center: { lat: number; lon: number; mgrs: string }
  gsd_m: number
}

export interface PipelineResult {
  detection: DetectionResult | null
  top_targets: DetectedAsset[]
  mission_summary: MissionSummary
  errors: Record<string, string>
  latency_ms: number
  image_wh: [number, number]
}

// ── Health ────────────────────────────────────────────────────────────────────
export interface HealthResult {
  status: string
  platform: string
  version: string
  device: string
  loaded_models: string[]
  gpu: Record<string, unknown>
  torch: string
  python: string
}

export type MissionContext = 'general' | 'anti_armor' | 'sead' | 'maritime'
export type AnalysisMode = 'pipeline' | 'detect' | 'fuse' | 'change'
