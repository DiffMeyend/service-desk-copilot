/**
 * TypeScript type definitions for QF_Wiz Context Payload
 * Mirrors the Python Pydantic schemas in api/schemas/
 */

// ============ Basic Types ============

export interface Requester {
  name: string;
  email: string;
  phone: string;
}

export interface TargetDevice {
  hostname: string;
  os: string;
  ip: string;
  asset_tag: string;
  serial_number: string;
  on_domain: boolean | null;
}

export interface UserContext {
  username: string;
  is_admin: boolean | null;
  is_remote: boolean | null;
}

export interface Network {
  connection_type: string;
  dns_servers: string[];
  vpn: boolean | null;
}

export interface ExecutionContext {
  tooling: string;
  run_as: string;
  privilege: string;
  sandbox_prepped: boolean | null;
}

export interface Environment {
  target_device: TargetDevice;
  user_context: UserContext;
  network: Network;
  execution_context: ExecutionContext;
}

export interface Impact {
  who: string;
  how_bad: string;
  work_stopped: boolean | null;
}

export interface Scope {
  single_user: boolean | null;
  multi_user: boolean | null;
  single_device: boolean | null;
  service_wide: boolean | null;
}

export interface Problem {
  symptoms: string[];
  impact: Impact;
  scope: Scope;
  start_time: string;
  last_known_good: string;
  recent_changes: string[];
}

export interface TestResult {
  command_id: string;
  output: string;
  captured_at: string;
}

export interface Hypothesis {
  id: string;
  hypothesis: string;
  confidence_hint: number;
  discriminating_question: string;
  discriminating_tests: string[];
  command_refs: string[];
  notes: string;
}

export interface ManualOverride {
  pack_id: string;
  loaded_at: string;
}

export interface Branches {
  active_hypotheses: Hypothesis[];
  collapsed_hypotheses: string[];
  current_best_guess: string;
  source_pack: string[];
  manual_overrides: ManualOverride[];
  routing_method: string;
}

export interface Evidence {
  tests_run: string[];
  results: TestResult[];
  observations: string[];
  discriminating_test: string;
  artifacts: {
    screenshots: string[];
    logs: string[];
    error_codes: string[];
  };
}

export interface CSSInfo {
  score: number;
  target: number;
  domain_scores: Record<string, number>;
  missing_fields: string[];
  contradictions: string[];
  confidence_notes: string;
}

export interface EscalateInfo {
  type: string;
  to_team: string;
  handoff_pack: Record<string, unknown>;
}

export interface Decision {
  status: DecisionStatus;
  recommended_outcome: string;
  reasoning: string[];
  if_escalate: EscalateInfo;
  resolution_choice: string;
  actual_root_cause: string;
  resolution_confidence: number | null;
  resolution_time_mins: number;
}

export type DecisionStatus =
  | 'triage'
  | 'testing'
  | 'converging'
  | 'decide'
  | 'resolved'
  | 'escalated_time'
  | 'escalated_skill';

export interface GuardrailChecks {
  confirmed: boolean;
  scope_confirmed: boolean;
  error_message_confirmed: boolean;
  repro_confirmed: boolean;
  connectivity_confirmed: boolean;
  authentication_confirmed: boolean;
  service_availability_confirmed: boolean;
  missing_checks: string[];
}

export interface Guardrails {
  basic_troubleshooting: GuardrailChecks;
}

export interface Notes {
  rolling: string;
  final: string;
  escalation: string;
}

export interface Meta {
  schema_version: string;
  session_id: string;
  last_updated: string;
  timezone: string;
}

export interface Ticket {
  id: string;
  created_at: string;
  company: string;
  site: string;
  priority: Priority;
  category: string;
  service: string;
  summary: string;
  raw_dump: string;
  requester: Requester;
}

export type Priority = 'P1' | 'P2' | 'P3' | 'P4' | 'P5' | 'UNKNOWN' | 'HIGH' | 'MEDIUM' | 'LOW';

// ============ Full Context Payload ============

export interface ContextPayload {
  meta: Meta;
  ticket: Ticket;
  environment: Environment;
  problem: Problem;
  evidence: Evidence;
  branches: Branches;
  css: CSSInfo;
  decision: Decision;
  guardrails: Guardrails;
  notes: Notes;
}

// ============ API Response Types ============

export interface TicketSummary {
  id: string;
  priority: Priority;
  company: string;
  summary: string;
  hostname: string;
  status: DecisionStatus;
  css_score: number;
  last_updated: string;
}

export interface CSSResponse {
  score: number;
  target: number;
  blockers: string[];
  domain_scores: Record<string, number>;
  missing_for_90: string[];
  can_decide: boolean;
}

export interface LogResultRequest {
  command_id: string;
  output: string;
  notes?: string;
  captured_at?: string;
}

export interface LogResultResponse {
  status: string;
  message: string;
  tests_run_count: number;
  css_score: number;
  claude_interpretation?: string;
}

export interface LoadBranchPackRequest {
  pack_id: string;
}

export interface LoadBranchPackResponse {
  status: string;
  message: string;
  pack_id: string;
  hypothesis_count: number;
}

export interface DecideRequest {
  force?: boolean;
}

export interface DecideResponse {
  status: string;
  message: string;
  decision_status: DecisionStatus;
  best_guess: string;
  css_score: number;
  warning?: string;
}

export interface NextActionResponse {
  action: 'load_pack' | 'decide' | 'run_test' | 'gather_evidence' | 'unknown';
  suggestion: string;
  hypothesis_id?: string;
  discriminating_test?: string;
  ai_reasoning?: string;
  ai_suggested_commands?: string[];
}

// ============ AI / Chat Types ============

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  response: string;
  hypothesis_updates: Record<string, string>;
  suggested_commands: string[];
}

export interface TriageInfo {
  routing_suggestion?: string;
  triage_reasoning?: string;
}

// ============ Branch Pack Types ============

export interface BranchPackSummary {
  id: string;
  name: string;
  category: string;
  goal: string;
  hypothesis_count: number;
  keywords: string[];
}

export interface BranchPackDetail {
  id: string;
  name: string;
  category: string;
  goal: string;
  notes: string;
  keywords: string[];
  signals: string[];
  hypotheses: Hypothesis[];
  preconditions: Record<string, unknown>;
}

// ============ WebSocket Message Types ============

export type WSMessage =
  | { type: 'cp_update'; payload: Partial<ContextPayload> }
  | { type: 'css_recalculated'; payload: { score: number; blockers: string[] } }
  | { type: 'hypothesis_collapsed'; payload: { id: string; reason: string } }
  | { type: 'decision_ready'; payload: { status: DecisionStatus } };
