// Health
export interface HealthResponse {
  status: string;
  version: string;
}

// Images
export interface ImageMeta {
  image_id: string;
  filename: string;
  purpose: 'analysis' | 'test';
  label: 'OK' | 'NG';
  path: string;
  uploaded_at: string;
}

export type UploadImageResponse = ImageMeta;
export type ImageListResponse = ImageMeta[];

export interface DeleteImageResponse {
  deleted: boolean;
}

export interface ClearImagesResponse {
  deleted_count: number;
}

// Config
export interface InspectionCriteria {
  accuracy?: number;
  fp_rate?: number;
  fn_rate?: number;
}

export interface AlignCriteria {
  coord_error?: number;
  success_rate?: number;
}

export interface ExecutionConfig {
  mode: 'inspection' | 'align';
  max_iteration: number;
  success_criteria: InspectionCriteria | AlignCriteria;
}

export interface SaveConfigResponse {
  config: ExecutionConfig;
  warnings?: string[];
}

// Directives
export interface AgentDirectives {
  orchestrator: string | null;
  spec: string | null;
  image_analysis: string | null;
  pipeline_composer: string | null;
  vision_judge: string | null;
  inspection_plan: string | null;
  algorithm_coder: string | null;
  test: string | null;
}

export interface DirectivesResponse {
  directives: AgentDirectives;
}

export interface UpdateDirectiveResponse {
  agent_name: string;
  directive: string;
}

export interface ResetDirectivesResponse {
  reset: boolean;
}

// Logs
export interface LogEntry {
  timestamp: string;
  agent: string;
  level: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface LogsResponse {
  logs: LogEntry[];
  total: number;
}

export interface LogAgentsResponse {
  agents: string[];
}

export interface ClearLogsResponse {
  cleared: boolean;
}

// Execute
export interface StartExecutionRequest {
  purpose_text: string;
}

export interface StartExecutionResponse {
  execution_id: string;
  status: string;
}

export interface ExecutionStatus {
  execution_id: string;
  status: string;
  current_agent: string | null;
  current_iteration: number;
  result: unknown | null;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export type ExecutionHistoryResponse = ExecutionStatus[];

export interface CancelExecutionResponse {
  cancelled: boolean;
}
