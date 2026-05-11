import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

const { mockExportCode, mockExportResult } = vi.hoisted(() => ({
  mockExportCode: vi.fn(),
  mockExportResult: vi.fn(),
}));

vi.mock('../services/api', () => ({
  exportCode: mockExportCode,
  exportResult: mockExportResult,
}));

import ExportButton from '../components/ExportButton';

beforeEach(() => {
  // jsdom does not implement URL.createObjectURL / revokeObjectURL
  Object.defineProperty(globalThis.URL, 'createObjectURL', {
    value: vi.fn(() => 'blob:mock-url'),
    writable: true,
    configurable: true,
  });
  Object.defineProperty(globalThis.URL, 'revokeObjectURL', {
    value: vi.fn(),
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('ExportButton — rendering', () => {
  it('renders the export button', () => {
    render(<ExportButton />);
    expect(screen.getByTestId('export-button')).toBeInTheDocument();
  });

  it('does not show dropdown menu initially', () => {
    render(<ExportButton />);
    expect(screen.queryByTestId('export-menu')).not.toBeInTheDocument();
  });

  it('shows dropdown menu after clicking button', () => {
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    expect(screen.getByTestId('export-menu')).toBeInTheDocument();
  });

  it('shows export code option in dropdown', () => {
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    expect(screen.getByTestId('export-code-option')).toBeInTheDocument();
  });

  it('shows export result option in dropdown', () => {
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    expect(screen.getByTestId('export-result-option')).toBeInTheDocument();
  });
});

describe('ExportButton — download code', () => {
  it('calls exportCode when export code option is clicked', async () => {
    mockExportCode.mockResolvedValue(new Blob(['import cv2'], { type: 'text/x-python' }));
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    fireEvent.click(screen.getByTestId('export-code-option'));
    await waitFor(() => expect(mockExportCode).toHaveBeenCalledOnce());
  });

  it('closes dropdown when export code is clicked', async () => {
    mockExportCode.mockResolvedValue(new Blob(['import cv2']));
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    expect(screen.getByTestId('export-menu')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('export-code-option'));
    await waitFor(() => expect(screen.queryByTestId('export-menu')).not.toBeInTheDocument());
  });
});

describe('ExportButton — download result', () => {
  it('calls exportResult when export result option is clicked', async () => {
    mockExportResult.mockResolvedValue(new Blob(['{}'], { type: 'application/json' }));
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    fireEvent.click(screen.getByTestId('export-result-option'));
    await waitFor(() => expect(mockExportResult).toHaveBeenCalledOnce());
  });

  it('closes dropdown when export result is clicked', async () => {
    mockExportResult.mockResolvedValue(new Blob(['{}']));
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    expect(screen.getByTestId('export-menu')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('export-result-option'));
    await waitFor(() => expect(screen.queryByTestId('export-menu')).not.toBeInTheDocument());
  });
});

describe('ExportButton — loading state', () => {
  it('shows loading indicator while downloading', async () => {
    let resolveExport!: (blob: Blob) => void;
    mockExportCode.mockReturnValue(
      new Promise<Blob>((res) => { resolveExport = res; }),
    );
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    fireEvent.click(screen.getByTestId('export-code-option'));
    expect(screen.getByTestId('export-loading')).toBeInTheDocument();
    resolveExport(new Blob(['import cv2']));
    await waitFor(() =>
      expect(screen.queryByTestId('export-loading')).not.toBeInTheDocument(),
    );
  });

  it('button is disabled while downloading', async () => {
    let resolveExport!: (blob: Blob) => void;
    mockExportCode.mockReturnValue(
      new Promise<Blob>((res) => { resolveExport = res; }),
    );
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    fireEvent.click(screen.getByTestId('export-code-option'));
    expect(screen.getByTestId('export-button')).toBeDisabled();
    resolveExport(new Blob(['import cv2']));
    await waitFor(() =>
      expect(screen.getByTestId('export-button')).not.toBeDisabled(),
    );
  });
});

describe('ExportButton — error state', () => {
  it('shows error message when export code fails', async () => {
    mockExportCode.mockRejectedValue(new Error('Network error'));
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    fireEvent.click(screen.getByTestId('export-code-option'));
    await waitFor(() =>
      expect(screen.getByTestId('export-error')).toBeInTheDocument(),
    );
  });

  it('shows error message when export result fails', async () => {
    mockExportResult.mockRejectedValue(new Error('Server error'));
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    fireEvent.click(screen.getByTestId('export-result-option'));
    await waitFor(() =>
      expect(screen.getByTestId('export-error')).toBeInTheDocument(),
    );
  });

  it('loading indicator disappears after error', async () => {
    mockExportCode.mockRejectedValue(new Error('fail'));
    render(<ExportButton />);
    fireEvent.click(screen.getByTestId('export-button'));
    fireEvent.click(screen.getByTestId('export-code-option'));
    await waitFor(() =>
      expect(screen.queryByTestId('export-loading')).not.toBeInTheDocument(),
    );
  });
});
