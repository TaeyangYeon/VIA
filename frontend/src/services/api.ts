import axios from 'axios';
import type {
  HealthResponse,
  ImageMeta,
  ImageListResponse,
  UploadImageResponse,
  DeleteImageResponse,
  ClearImagesResponse,
  ExecutionConfig,
  SaveConfigResponse,
  AgentDirectives,
  DirectivesResponse,
  UpdateDirectiveResponse,
  ResetDirectivesResponse,
  LogsResponse,
  LogAgentsResponse,
  ClearLogsResponse,
  StartExecutionResponse,
  ExecutionStatus,
  ExecutionHistoryResponse,
  CancelExecutionResponse,
} from './types';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
});

// Health

export async function checkHealth(): Promise<HealthResponse> {
  const res = await apiClient.get<HealthResponse>('/health');
  return res.data;
}

// Images

export async function uploadImage(
  file: File,
  purpose: 'analysis' | 'test',
): Promise<UploadImageResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post<UploadImageResponse>('/api/images/upload', formData, {
    params: { purpose },
  });
  return res.data;
}

export async function getImages(params?: {
  purpose?: string;
  label?: string;
}): Promise<ImageListResponse> {
  const res = await apiClient.get<ImageListResponse>('/api/images', {
    params: params ?? {},
  });
  return res.data;
}

export async function getImage(imageId: string): Promise<ImageMeta> {
  const res = await apiClient.get<ImageMeta>(`/api/images/${imageId}`);
  return res.data;
}

export async function deleteImage(imageId: string): Promise<DeleteImageResponse> {
  const res = await apiClient.delete<DeleteImageResponse>(`/api/images/${imageId}`);
  return res.data;
}

export async function clearImages(purpose?: string): Promise<ClearImagesResponse> {
  const res = await apiClient.delete<ClearImagesResponse>('/api/images', {
    params: purpose ? { purpose } : {},
  });
  return res.data;
}

// Config

export async function saveConfig(config: ExecutionConfig): Promise<SaveConfigResponse> {
  const res = await apiClient.post<SaveConfigResponse>('/api/config', config);
  return res.data;
}

export async function getConfig(): Promise<ExecutionConfig> {
  const res = await apiClient.get<ExecutionConfig>('/api/config');
  return res.data;
}

// Directives

export async function getDirectives(): Promise<AgentDirectives> {
  const res = await apiClient.get<AgentDirectives>('/api/directives');
  return res.data;
}

export async function saveDirectives(
  directives: Partial<AgentDirectives>,
): Promise<DirectivesResponse> {
  const res = await apiClient.post<DirectivesResponse>('/api/directives', directives);
  return res.data;
}

export async function updateDirective(
  agentName: string,
  directive: string,
): Promise<UpdateDirectiveResponse> {
  const res = await apiClient.put<UpdateDirectiveResponse>(`/api/directives/${agentName}`, {
    directive,
  });
  return res.data;
}

export async function resetDirectives(): Promise<ResetDirectivesResponse> {
  const res = await apiClient.delete<ResetDirectivesResponse>('/api/directives');
  return res.data;
}

// Logs

export async function getLogs(params?: {
  agent?: string;
  level?: string;
  limit?: number;
}): Promise<LogsResponse> {
  const res = await apiClient.get<LogsResponse>('/api/logs', {
    params: params ?? {},
  });
  return res.data;
}

export async function getLogAgents(): Promise<LogAgentsResponse> {
  const res = await apiClient.get<LogAgentsResponse>('/api/logs/agents');
  return res.data;
}

export async function clearLogs(): Promise<ClearLogsResponse> {
  const res = await apiClient.delete<ClearLogsResponse>('/api/logs');
  return res.data;
}

// Execute

export async function startExecution(purposeText: string): Promise<StartExecutionResponse> {
  const res = await apiClient.post<StartExecutionResponse>(
    '/api/execute',
    { purpose_text: purposeText },
    { timeout: 600000 },
  );
  return res.data;
}

export async function getExecutionStatus(executionId: string): Promise<ExecutionStatus> {
  const res = await apiClient.get<ExecutionStatus>(`/api/execute/${executionId}`);
  return res.data;
}

export async function getExecutionHistory(): Promise<ExecutionHistoryResponse> {
  const res = await apiClient.get<ExecutionHistoryResponse>('/api/execute/history');
  return res.data;
}

export async function cancelExecution(executionId: string): Promise<CancelExecutionResponse> {
  const res = await apiClient.post<CancelExecutionResponse>(`/api/execute/${executionId}/cancel`);
  return res.data;
}
