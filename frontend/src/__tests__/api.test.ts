import { vi, describe, it, expect, beforeEach } from 'vitest';

const { mockGet, mockPost, mockPut, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
  mockDelete: vi.fn(),
}));

vi.mock('axios', () => ({
  default: {
    create: vi.fn().mockReturnValue({
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
    }),
  },
}));

import axios from 'axios';
import {
  checkHealth,
  uploadImage,
  getImages,
  getImage,
  deleteImage,
  clearImages,
  saveConfig,
  getConfig,
  getDirectives,
  saveDirectives,
  updateDirective,
  resetDirectives,
  getLogs,
  getLogAgents,
  clearLogs,
  startExecution,
  getExecutionStatus,
  getExecutionHistory,
  cancelExecution,
} from '../services/api';

const axiosCreateConfig = (axios.create as ReturnType<typeof vi.fn>).mock.calls[0]?.[0];

// ────────────────────────────────────────────────
// a. axios instance config
// ────────────────────────────────────────────────

describe('a. axios instance config', () => {
  it('creates instance with baseURL http://localhost:8000', () => {
    expect(axiosCreateConfig?.baseURL).toBe('http://localhost:8000');
  });

  it('creates instance with default timeout 30000', () => {
    expect(axiosCreateConfig?.timeout).toBe(30000);
  });
});

// ────────────────────────────────────────────────
// b. Health API
// ────────────────────────────────────────────────

describe('b. Health API', () => {
  beforeEach(() => vi.clearAllMocks());

  it('checkHealth calls GET /health and returns data', async () => {
    mockGet.mockResolvedValueOnce({ data: { status: 'ok', version: '1.0.0' } });
    const result = await checkHealth();
    expect(mockGet).toHaveBeenCalledWith('/health');
    expect(result).toEqual({ status: 'ok', version: '1.0.0' });
  });
});

// ────────────────────────────────────────────────
// c. Images API
// ────────────────────────────────────────────────

describe('c. Images API', () => {
  beforeEach(() => vi.clearAllMocks());

  const mockImage = {
    image_id: 'img-1',
    filename: 'test.png',
    purpose: 'analysis' as const,
    label: 'OK' as const,
    path: '/tmp/test.png',
    uploaded_at: '2026-01-01T00:00:00Z',
  };

  it('uploadImage calls POST /api/images/upload with FormData and purpose param', async () => {
    mockPost.mockResolvedValueOnce({ data: mockImage });
    const file = new File(['data'], 'test.png', { type: 'image/png' });
    const result = await uploadImage(file, 'analysis');
    expect(mockPost).toHaveBeenCalledWith(
      '/api/images/upload',
      expect.any(FormData),
      expect.objectContaining({ params: { purpose: 'analysis' } }),
    );
    expect(result).toEqual(mockImage);
  });

  it('getImages calls GET /api/images with empty params when none provided', async () => {
    mockGet.mockResolvedValueOnce({ data: [mockImage] });
    const result = await getImages();
    expect(mockGet).toHaveBeenCalledWith('/api/images', { params: {} });
    expect(result).toEqual([mockImage]);
  });

  it('getImages passes purpose and label filters', async () => {
    mockGet.mockResolvedValueOnce({ data: [mockImage] });
    await getImages({ purpose: 'analysis', label: 'OK' });
    expect(mockGet).toHaveBeenCalledWith('/api/images', {
      params: { purpose: 'analysis', label: 'OK' },
    });
  });

  it('getImage calls GET /api/images/{image_id} and returns data', async () => {
    mockGet.mockResolvedValueOnce({ data: mockImage });
    const result = await getImage('img-1');
    expect(mockGet).toHaveBeenCalledWith('/api/images/img-1');
    expect(result).toEqual(mockImage);
  });

  it('deleteImage calls DELETE /api/images/{image_id} and returns result', async () => {
    mockDelete.mockResolvedValueOnce({ data: { deleted: true } });
    const result = await deleteImage('img-1');
    expect(mockDelete).toHaveBeenCalledWith('/api/images/img-1');
    expect(result).toEqual({ deleted: true });
  });

  it('clearImages calls DELETE /api/images with empty params when no purpose', async () => {
    mockDelete.mockResolvedValueOnce({ data: { deleted_count: 5 } });
    const result = await clearImages();
    expect(mockDelete).toHaveBeenCalledWith('/api/images', { params: {} });
    expect(result).toEqual({ deleted_count: 5 });
  });

  it('clearImages passes purpose param when provided', async () => {
    mockDelete.mockResolvedValueOnce({ data: { deleted_count: 3 } });
    await clearImages('analysis');
    expect(mockDelete).toHaveBeenCalledWith('/api/images', { params: { purpose: 'analysis' } });
  });
});

// ────────────────────────────────────────────────
// d. Config API
// ────────────────────────────────────────────────

describe('d. Config API', () => {
  beforeEach(() => vi.clearAllMocks());

  const mockConfig = {
    mode: 'inspection' as const,
    max_iteration: 10,
    success_criteria: { accuracy: 0.95, fp_rate: 0.05, fn_rate: 0.05 },
  };

  it('saveConfig calls POST /api/config and returns SaveConfigResponse', async () => {
    mockPost.mockResolvedValueOnce({ data: { config: mockConfig, warnings: [] } });
    const result = await saveConfig(mockConfig);
    expect(mockPost).toHaveBeenCalledWith('/api/config', mockConfig);
    expect(result).toEqual({ config: mockConfig, warnings: [] });
  });

  it('getConfig calls GET /api/config and returns ExecutionConfig', async () => {
    mockGet.mockResolvedValueOnce({ data: mockConfig });
    const result = await getConfig();
    expect(mockGet).toHaveBeenCalledWith('/api/config');
    expect(result).toEqual(mockConfig);
  });
});

// ────────────────────────────────────────────────
// e. Directives API
// ────────────────────────────────────────────────

describe('e. Directives API', () => {
  beforeEach(() => vi.clearAllMocks());

  const mockDirectives = {
    orchestrator: 'do X',
    spec: null,
    image_analysis: null,
    pipeline_composer: null,
    vision_judge: null,
    inspection_plan: null,
    algorithm_coder: null,
    test: null,
  };

  it('getDirectives calls GET /api/directives and returns AgentDirectives', async () => {
    mockGet.mockResolvedValueOnce({ data: mockDirectives });
    const result = await getDirectives();
    expect(mockGet).toHaveBeenCalledWith('/api/directives');
    expect(result).toEqual(mockDirectives);
  });

  it('saveDirectives calls POST /api/directives with partial directives', async () => {
    const partial = { orchestrator: 'do X' };
    mockPost.mockResolvedValueOnce({ data: { directives: mockDirectives } });
    const result = await saveDirectives(partial);
    expect(mockPost).toHaveBeenCalledWith('/api/directives', partial);
    expect(result).toEqual({ directives: mockDirectives });
  });

  it('updateDirective calls PUT /api/directives/{agent_name} with directive body', async () => {
    mockPut.mockResolvedValueOnce({
      data: { agent_name: 'orchestrator', directive: 'new directive' },
    });
    const result = await updateDirective('orchestrator', 'new directive');
    expect(mockPut).toHaveBeenCalledWith('/api/directives/orchestrator', {
      directive: 'new directive',
    });
    expect(result).toEqual({ agent_name: 'orchestrator', directive: 'new directive' });
  });

  it('resetDirectives calls DELETE /api/directives', async () => {
    mockDelete.mockResolvedValueOnce({ data: { reset: true } });
    const result = await resetDirectives();
    expect(mockDelete).toHaveBeenCalledWith('/api/directives');
    expect(result).toEqual({ reset: true });
  });
});

// ────────────────────────────────────────────────
// f. Logs API
// ────────────────────────────────────────────────

describe('f. Logs API', () => {
  beforeEach(() => vi.clearAllMocks());

  it('getLogs calls GET /api/logs with empty params when none provided', async () => {
    mockGet.mockResolvedValueOnce({ data: { logs: [], total: 0 } });
    const result = await getLogs();
    expect(mockGet).toHaveBeenCalledWith('/api/logs', { params: {} });
    expect(result).toEqual({ logs: [], total: 0 });
  });

  it('getLogs passes agent, level, limit filters', async () => {
    mockGet.mockResolvedValueOnce({ data: { logs: [], total: 0 } });
    await getLogs({ agent: 'orchestrator', level: 'INFO', limit: 50 });
    expect(mockGet).toHaveBeenCalledWith('/api/logs', {
      params: { agent: 'orchestrator', level: 'INFO', limit: 50 },
    });
  });

  it('getLogAgents calls GET /api/logs/agents and returns agents list', async () => {
    mockGet.mockResolvedValueOnce({ data: { agents: ['orchestrator', 'spec'] } });
    const result = await getLogAgents();
    expect(mockGet).toHaveBeenCalledWith('/api/logs/agents');
    expect(result).toEqual({ agents: ['orchestrator', 'spec'] });
  });

  it('clearLogs calls DELETE /api/logs', async () => {
    mockDelete.mockResolvedValueOnce({ data: { cleared: true } });
    const result = await clearLogs();
    expect(mockDelete).toHaveBeenCalledWith('/api/logs');
    expect(result).toEqual({ cleared: true });
  });
});

// ────────────────────────────────────────────────
// g. Execute API
// ────────────────────────────────────────────────

describe('g. Execute API', () => {
  beforeEach(() => vi.clearAllMocks());

  const mockExecutionStatus = {
    execution_id: 'exec-1',
    status: 'running',
    current_agent: 'orchestrator',
    current_iteration: 1,
    result: null,
    error: null,
    started_at: '2026-01-01T00:00:00Z',
    completed_at: null,
  };

  it('startExecution calls POST /api/execute with purpose_text and 600000 timeout', async () => {
    mockPost.mockResolvedValueOnce({ data: { execution_id: 'exec-1', status: 'running' } });
    const result = await startExecution('detect cracks');
    expect(mockPost).toHaveBeenCalledWith(
      '/api/execute',
      { purpose_text: 'detect cracks' },
      { timeout: 600000 },
    );
    expect(result).toEqual({ execution_id: 'exec-1', status: 'running' });
  });

  it('getExecutionStatus calls GET /api/execute/{execution_id}', async () => {
    mockGet.mockResolvedValueOnce({ data: mockExecutionStatus });
    const result = await getExecutionStatus('exec-1');
    expect(mockGet).toHaveBeenCalledWith('/api/execute/exec-1');
    expect(result).toEqual(mockExecutionStatus);
  });

  it('getExecutionHistory calls GET /api/execute/history', async () => {
    mockGet.mockResolvedValueOnce({ data: [mockExecutionStatus] });
    const result = await getExecutionHistory();
    expect(mockGet).toHaveBeenCalledWith('/api/execute/history');
    expect(result).toEqual([mockExecutionStatus]);
  });

  it('cancelExecution calls POST /api/execute/{execution_id}/cancel', async () => {
    mockPost.mockResolvedValueOnce({ data: { cancelled: true } });
    const result = await cancelExecution('exec-1');
    expect(mockPost).toHaveBeenCalledWith('/api/execute/exec-1/cancel');
    expect(result).toEqual({ cancelled: true });
  });
});

// ────────────────────────────────────────────────
// h. Error handling
// ────────────────────────────────────────────────

describe('h. Error handling', () => {
  beforeEach(() => vi.clearAllMocks());

  it('propagates network errors from checkHealth', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network Error'));
    await expect(checkHealth()).rejects.toThrow('Network Error');
  });

  it('propagates 404 axios errors from getImage', async () => {
    const error = Object.assign(new Error('Not found'), {
      response: { status: 404, data: { detail: 'Not found' } },
      isAxiosError: true,
    });
    mockGet.mockRejectedValueOnce(error);
    await expect(getImage('nonexistent')).rejects.toMatchObject({
      response: { status: 404 },
    });
  });

  it('propagates 5xx server errors from startExecution', async () => {
    const error = Object.assign(new Error('Internal Server Error'), {
      response: { status: 500, data: { detail: 'Server error' } },
      isAxiosError: true,
    });
    mockPost.mockRejectedValueOnce(error);
    await expect(startExecution('test')).rejects.toMatchObject({
      response: { status: 500 },
    });
  });
});
