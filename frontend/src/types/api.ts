/** Typed API response and entity interfaces. */

// ── Envelope ────────────────────────────────────────────
export interface ApiResponse<T = unknown> {
  request_id: string;
  code: number;
  message: string;
  data: T;
}

export interface ApiError {
  request_id: string;
  code: number;
  message: string;
  details?: unknown;
}

// ── Auth ────────────────────────────────────────────────
export interface DevLoginResponse {
  access_token: string;
  token_type: string;
  tenant_id: string;
  user_id: string;
  role: string;
}

// ── Document ────────────────────────────────────────────
export interface InitUploadResponse {
  upload_id: string;
  doc_id: string;
}

export interface CompleteUploadResponse {
  upload_id: string;
  doc_id: string;
  status: string;
}

export interface DocumentOut {
  doc_id: string;
  filename: string;
  file_size: number | null;
  mime_type: string;
  page_count: number | null;
  status: string;
  created_at: string;
}

export interface DocumentVersionOut {
  version_id: string;
  doc_id: string;
  version_no: number;
  status: string;
  parse_params: Record<string, unknown> | null;
  created_at: string;
}

// ── Job ─────────────────────────────────────────────────
export interface JobOut {
  job_id: string;
  version_id: string;
  doc_id: string;
  stage: string;
  progress: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface JobEventData {
  job_id: string;
  stage: string;
  progress: number;
  message?: string;
  error?: string;
}

// ── Result / Dashboard ──────────────────────────────────
export interface EvidenceRef {
  ref_id: string;
  page_no: number;
  bbox_norm: number[] | null;
  snippet: string | null;
}

export interface MetricValue {
  mv_id: string;
  metric_code: string;
  metric_name_cn: string;
  unit: string | null;
  period: string;
  value: number | null;
  value_text: string | null;
  yoy_change: number | null;
  needs_review: boolean;
  evidence_refs: EvidenceRef[];
}

export interface RiskItem {
  risk_id: string;
  level: 'high' | 'medium' | 'low';
  title: string;
  description: string | null;
  recommendation: string | null;
  needs_review: boolean;
  evidence_refs: EvidenceRef[];
}

export interface DashboardResult {
  version_id: string;
  doc_id: string;
  summary: string | null;
  metrics: MetricValue[];
  risks: RiskItem[];
  page_count: number;
}

// ── Export ───────────────────────────────────────────────
export interface ExportOut {
  export_id: string;
  version_id: string;
  format: string;
  status: string;
  file_path: string | null;
  error_message: string | null;
  created_at: string;
}

// ── Chat ────────────────────────────────────────────────
export interface ChatSession {
  session_id: string;
  version_id: string;
  title: string | null;
  created_at: string;
}

export interface ChatMessage {
  message_id: string;
  role: 'user' | 'assistant';
  content: string | null;
  evidence_refs: EvidenceRef[] | null;
  created_at: string;
}
