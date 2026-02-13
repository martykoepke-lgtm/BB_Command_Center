/**
 * TypeScript interfaces matching the FastAPI Pydantic schemas.
 * Kept in sync with backend/app/schemas/*.py
 */

// ---- Common ----

export type UserRole = "admin" | "manager" | "analyst" | "viewer" | "sponsor";
export type RequestStatus = "submitted" | "under_review" | "accepted" | "declined" | "converted";
export type Urgency = "critical" | "high" | "medium" | "low";
export type Priority = "critical" | "high" | "medium" | "low";
export type Methodology = "DMAIC" | "Kaizen" | "A3" | "PDSA" | "custom";
export type InitiativeStatus = "active" | "on_hold" | "completed" | "cancelled";
export type PhaseStatus = "not_started" | "in_progress" | "completed" | "skipped";
export type PhaseName = "define" | "measure" | "analyze" | "improve" | "control";
export type ActionStatus = "open" | "in_progress" | "completed" | "cancelled";
export type AnalysisStatus = "pending" | "running" | "completed" | "failed";
export type WorkItemType = "initiative" | "consultation" | "work_assignment";

// ---- Auth ----

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  title: string | null;
  role: UserRole;
  avatar_url: string | null;
  skills: string[];
  capacity_hours: number;
  is_active: boolean;
  created_at: string;
}

// ---- Requests ----

export interface RequestCreate {
  title: string;
  description?: string;
  requester_name: string;
  requester_email?: string;
  requester_dept?: string;
  problem_statement?: string;
  desired_outcome?: string;
  business_impact?: string;
  urgency?: Urgency;
}

export interface RequestOut {
  id: string;
  request_number: string;
  title: string;
  description: string | null;
  requester_name: string;
  requester_email: string | null;
  requester_dept: string | null;
  problem_statement: string | null;
  desired_outcome: string | null;
  business_impact: string | null;
  urgency: Urgency;
  complexity_score: number | null;
  recommended_methodology: string | null;
  status: RequestStatus;
  review_notes: string | null;
  submitted_at: string;
  reviewed_at: string | null;
}

// ---- Initiatives ----

export interface InitiativeCreate {
  title: string;
  problem_statement: string;
  desired_outcome: string;
  methodology?: Methodology;
  initiative_type?: WorkItemType;
  priority?: Priority;
  scope?: string;
  request_id?: string;
}

export interface InitiativeOut {
  id: string;
  initiative_number: string;
  title: string;
  problem_statement: string;
  desired_outcome: string;
  scope: string | null;
  out_of_scope: string | null;
  business_case: string | null;
  methodology: Methodology;
  initiative_type: string | null;
  priority: Priority;
  status: InitiativeStatus;
  lead_analyst_id: string | null;
  team_id: string | null;
  sponsor_id: string | null;
  start_date: string | null;
  target_completion: string | null;
  actual_completion: string | null;
  current_phase: string;
  phase_progress: Record<string, number>;
  projected_savings: number | null;
  actual_savings: number | null;
  tags: string[];
  created_at: string;
  updated_at: string;

  // Nested
  phases: PhaseOut[];
}

export interface InitiativeSummary {
  id: string;
  initiative_number: string;
  title: string;
  methodology: Methodology;
  initiative_type: WorkItemType | null;
  priority: Priority;
  status: InitiativeStatus;
  current_phase: string;
  lead_analyst_id: string | null;
  team_id: string | null;
  created_at: string;
}

// ---- Phases ----

export interface PhaseOut {
  id: string;
  initiative_id: string;
  phase_name: string;
  phase_order: number;
  status: PhaseStatus;
  started_at: string | null;
  completed_at: string | null;
  gate_approved: boolean;
  ai_summary: string | null;
  completeness_score: number;
}

// ---- Teams ----

export interface TeamOut {
  id: string;
  name: string;
  description: string | null;
  department: string | null;
  organization: string | null;
  manager_id: string | null;
  created_at: string;
  member_count?: number;
}

export interface TeamMemberOut {
  user_id: string;
  full_name: string;
  email: string;
  role: UserRole;
  role_in_team: string;
}

// ---- Team Dashboard ----

export interface MemberMetrics {
  user_id: string;
  full_name: string;
  capacity_hours: number;
  allocated_hours: number;
  utilization_pct: number;
  active_initiative_count: number;
  initiatives: { id: string; title: string; status: string }[];
}

export interface InitiativeSummaryItem {
  id: string;
  initiative_number: string;
  title: string;
  status: string;
  current_phase: string;
  priority: string;
  methodology: string | null;
  lead_analyst_id: string | null;
  health_score: string | null;
}

export interface TeamMetrics {
  team_id: string;
  team_name: string;
  member_count: number;
  average_utilization: number;
  members: MemberMetrics[];
  initiatives: InitiativeSummaryItem[];
  action_compliance: {
    on_time_pct?: number;
    overdue_count?: number;
    total_completed?: number;
  };
  overloaded: string[];
  available: string[];
}

// ---- Action Items ----

export interface ActionItemOut {
  id: string;
  initiative_id: string;
  title: string;
  description: string | null;
  assigned_to: string | null;
  status: ActionStatus;
  priority: Priority;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
}

// ---- Statistical Analysis ----

export interface AnalysisCreate {
  dataset_id: string;
  test_type: string;
  test_category: string;
  configuration: Record<string, unknown>;
}

export interface AnalysisOut {
  id: string;
  initiative_id: string;
  dataset_id: string | null;
  test_type: string;
  test_category: string;
  status: AnalysisStatus;
  configuration: Record<string, unknown>;
  results: Record<string, unknown> | null;
  charts: Record<string, unknown> | null;
  duration_ms: number | null;
  run_at: string | null;
  created_at: string;
}

// ---- Dashboard ----

export interface PortfolioDashboard {
  initiative_counts: Record<string, number>;
  action_counts: Record<string, number>;
  savings: Record<string, number>;
  utilization: Record<string, number>;
  phase_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  methodology_distribution: Record<string, number>;
  trends: { month: string; count: number; projected_savings: number; actual_savings: number }[];
  health_summary: Record<string, number>;
  upcoming_deadlines: {
    action_item_id: string;
    title: string;
    due_date: string;
    priority: string;
    status: string;
    initiative_id?: string;
    initiative_number?: string;
    initiative_title?: string;
    owner_name?: string;
  }[];
}

export interface PipelineDashboard {
  total_requests: number;
  by_status: Record<string, number>;
  by_urgency: Record<string, number>;
  conversion_rate: number;
  recent_requests: RequestOut[];
}

// ---- Paginated response ----

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
