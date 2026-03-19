// Mirrors Pydantic schemas in app/schemas/

export interface ProfileCreate {
  name: string
  targets?: string[] | null
  constraints?: string[] | null
  skills?: string[] | null
}

export interface ProfileUpdate {
  name?: string | null
  targets?: string[] | null
  constraints?: string[] | null
  skills?: string[] | null
}

export interface Profile {
  id: string
  name: string
  targets: string[] | null
  constraints: string[] | null
  skills: string[] | null
  cv_path: string | null
  created_at: string
  updated_at: string
}

export interface RunCreate {
  mode: "daily" | "weekly" | "cover_letter"
  options?: Record<string, unknown> | null
}

export interface Run {
  id: string
  profile_id: string
  mode: string
  status: string
  started_at: string | null
  finished_at: string | null
  verifier_status: string | null
  audit_path: string | null
}

// --- 5 entity types (replace old Opportunity) ---

export interface JobOpportunity {
  id: string
  profile_id: string
  run_id: string
  title: string
  company: string | null
  url: string | null
  description: string | null
  location: string | null
  salary_range: string | null
  source_query: string | null
  created_at: string
}

export interface Certification {
  id: string
  profile_id: string
  run_id: string
  title: string
  provider: string | null
  url: string | null
  description: string | null
  cost: string | null
  duration: string | null
  created_at: string
}

export interface Course {
  id: string
  profile_id: string
  run_id: string
  title: string
  platform: string | null
  url: string | null
  description: string | null
  cost: string | null
  duration: string | null
  created_at: string
}

export interface Event {
  id: string
  profile_id: string
  run_id: string
  title: string
  organizer: string | null
  url: string | null
  description: string | null
  event_date: string | null
  location: string | null
  created_at: string
}

export interface Group {
  id: string
  profile_id: string
  run_id: string
  title: string
  platform: string | null
  url: string | null
  description: string | null
  member_count: number | null
  created_at: string
}

export interface Trend {
  id: string
  profile_id: string
  run_id: string
  title: string
  category: string | null
  url: string | null
  description: string | null
  relevance: string | null
  source: string | null
  created_at: string
}

export interface ResultTitleUpdate {
  title: string
}

export interface CoverLetterCreate {
  job_opportunity_id?: string | null
  jd_text?: string | null
}

export interface CoverLetter {
  id: string
  profile_id: string
  job_opportunity_id: string | null
  run_id: string | null
  content: string
  created_at: string
}

export interface Policy {
  name: string
  content: Record<string, unknown>
}

export interface SSEEvent {
  type: string
  run_id?: string
  agent?: string
  status?: string
  error?: string
  timestamp?: string
  mode?: string
}

export interface AuditEvent {
  timestamp: string
  event_type: string
  agent: string
  data: Record<string, unknown>
}

export interface AuditTrail {
  run_id: string
  events: AuditEvent[]
}

export interface ReplayRequest {
  mode: "strict" | "refresh"
}

export interface ReplayResponse {
  run_id: string
  replay_mode: string
  original_run_id: string
  result: Record<string, unknown>
  verifier_report: Record<string, unknown>
  drift: unknown[]
}

export interface DiffResponse {
  run_a: string
  run_b: string
  additions: unknown[]
  removals: unknown[]
  changes: unknown[]
  summary: Record<string, unknown>
}
