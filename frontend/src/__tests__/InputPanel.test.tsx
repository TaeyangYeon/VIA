import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import InputPanel, { validateFilename } from '../components/panels/InputPanel';
import projectReducer from '../store/slices/projectSlice';
import imagesReducer from '../store/slices/imagesSlice';
import configReducer from '../store/slices/configSlice';
import directivesReducer from '../store/slices/directivesSlice';
import executionReducer from '../store/slices/executionSlice';
import resultReducer from '../store/slices/resultSlice';
import logsReducer from '../store/slices/logsSlice';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  uploadImage: vi.fn(),
  deleteImage: vi.fn(),
  clearImages: vi.fn(),
}));

beforeAll(() => {
  global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test-url');
  global.URL.revokeObjectURL = vi.fn();
});

const createTestStore = () =>
  configureStore({
    reducer: {
      project: projectReducer,
      images: imagesReducer,
      config: configReducer,
      directives: directivesReducer,
      execution: executionReducer,
      result: resultReducer,
      logs: logsReducer,
    },
  });

const renderInputPanel = () => {
  const store = createTestStore();
  const result = render(
    <Provider store={store}>
      <InputPanel />
    </Provider>,
  );
  return { ...result, store };
};

const makeFile = (name: string) => new File(['img-data'], name, { type: 'image/png' });

const makeApiImage = (
  label: 'OK' | 'NG',
  name: string,
  purpose: 'analysis' | 'test',
  id = `${label.toLowerCase()}-1`,
) => ({
  image_id: id,
  filename: name,
  purpose,
  label,
  path: `/tmp/${name}`,
  uploaded_at: '2026-01-01T00:00:00Z',
});

// ── validateFilename ───────────────────────────────────────────

describe('validateFilename', () => {
  it('accepts OK_1.png', () => {
    expect(validateFilename('OK_1.png')).toBe(true);
  });

  it('accepts NG_2.jpg', () => {
    expect(validateFilename('NG_2.jpg')).toBe(true);
  });

  it('accepts ok_3.jpeg (case-insensitive)', () => {
    expect(validateFilename('ok_3.jpeg')).toBe(true);
  });

  it('accepts NG_100.bmp', () => {
    expect(validateFilename('NG_100.bmp')).toBe(true);
  });

  it('accepts OK_1.tiff', () => {
    expect(validateFilename('OK_1.tiff')).toBe(true);
  });

  it('accepts OK_1.TIFF (uppercase extension)', () => {
    expect(validateFilename('OK_1.TIFF')).toBe(true);
  });

  it('rejects test.png (no OK/NG prefix)', () => {
    expect(validateFilename('test.png')).toBe(false);
  });

  it('rejects OK.png (missing _N)', () => {
    expect(validateFilename('OK.png')).toBe(false);
  });

  it('rejects OK_abc.png (non-numeric N)', () => {
    expect(validateFilename('OK_abc.png')).toBe(false);
  });

  it('rejects OK_1.gif (unsupported format)', () => {
    expect(validateFilename('OK_1.gif')).toBe(false);
  });

  it('rejects empty string', () => {
    expect(validateFilename('')).toBe(false);
  });
});

// ── Section rendering ──────────────────────────────────────────

describe('InputPanel — section rendering', () => {
  it('renders Analysis Images section heading', () => {
    renderInputPanel();
    expect(screen.getByText(/Analysis Images/i)).toBeInTheDocument();
  });

  it('renders Test Images section heading', () => {
    renderInputPanel();
    expect(screen.getByText(/Test Images/i)).toBeInTheDocument();
  });

  it('renders analysis drop zone', () => {
    renderInputPanel();
    expect(screen.getByTestId('analysis-drop-zone')).toBeInTheDocument();
  });

  it('renders test drop zone', () => {
    renderInputPanel();
    expect(screen.getByTestId('test-drop-zone')).toBeInTheDocument();
  });

  it('renders analysis file input', () => {
    renderInputPanel();
    expect(screen.getByTestId('analysis-file-input')).toBeInTheDocument();
  });

  it('renders test file input', () => {
    renderInputPanel();
    expect(screen.getByTestId('test-file-input')).toBeInTheDocument();
  });
});

// ── Empty state ────────────────────────────────────────────────

describe('InputPanel — empty state', () => {
  it('shows 0 count for analysis images initially', () => {
    renderInputPanel();
    expect(screen.getByTestId('analysis-count')).toHaveTextContent('0');
  });

  it('shows 0 count for test images initially', () => {
    renderInputPanel();
    expect(screen.getByTestId('test-count')).toHaveTextContent('0');
  });

  it('shows drop hint text in analysis zone when empty', () => {
    renderInputPanel();
    const zone = screen.getByTestId('analysis-drop-zone');
    expect(zone.textContent).toMatch(/drop|drag|upload/i);
  });

  it('shows drop hint text in test zone when empty', () => {
    renderInputPanel();
    const zone = screen.getByTestId('test-drop-zone');
    expect(zone.textContent).toMatch(/drop|drag|upload/i);
  });
});

// ── File validation ────────────────────────────────────────────

describe('InputPanel — file validation', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows validation error for invalid filename via file input', async () => {
    renderInputPanel();
    const input = screen.getByTestId('analysis-file-input');
    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile('invalid_name.png')] } });
    });
    expect(screen.getByText(/invalid|OK_N|NG_N|filename/i)).toBeInTheDocument();
  });

  it('does not call uploadImage for invalid filename', async () => {
    renderInputPanel();
    const input = screen.getByTestId('analysis-file-input');
    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile('random.png')] } });
    });
    expect(api.uploadImage).not.toHaveBeenCalled();
  });

  it('does not show error for valid filename', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    renderInputPanel();
    const input = screen.getByTestId('analysis-file-input');
    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile('OK_1.png')] } });
    });
    await waitFor(() => {
      expect(screen.queryByText(/invalid filename/i)).not.toBeInTheDocument();
    });
  });
});

// ── Upload flow ────────────────────────────────────────────────

describe('InputPanel — upload flow', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls uploadImage with file and purpose=analysis', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    renderInputPanel();
    const file = makeFile('OK_1.png');
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [file] },
      });
    });
    await waitFor(() => {
      expect(api.uploadImage).toHaveBeenCalledWith(file, 'analysis');
    });
  });

  it('calls uploadImage with file and purpose=test', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('NG', 'NG_1.png', 'test'),
    );
    renderInputPanel();
    const file = makeFile('NG_1.png');
    await act(async () => {
      fireEvent.change(screen.getByTestId('test-file-input'), {
        target: { files: [file] },
      });
    });
    await waitFor(() => {
      expect(api.uploadImage).toHaveBeenCalledWith(file, 'test');
    });
  });

  it('dispatches addImage and updates store after analysis upload', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    const { store } = renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => {
      expect(store.getState().images.analysis).toHaveLength(1);
    });
  });

  it('dispatches addImage and updates store after test upload', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('NG', 'NG_1.png', 'test'),
    );
    const { store } = renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('test-file-input'), {
        target: { files: [makeFile('NG_1.png')] },
      });
    });
    await waitFor(() => {
      expect(store.getState().images.test).toHaveLength(1);
    });
  });

  it('shows error when upload API fails', async () => {
    vi.mocked(api.uploadImage).mockRejectedValueOnce(new Error('Upload failed'));
    renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => {
      expect(screen.getByText(/upload failed|error/i)).toBeInTheDocument();
    });
  });
});

// ── Thumbnail display ──────────────────────────────────────────

describe('InputPanel — thumbnail display', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows thumbnail with filename after upload', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => {
      expect(screen.getByText('OK_1.png')).toBeInTheDocument();
    });
  });

  it('shows OK badge for OK image', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => {
      expect(screen.getByText('OK')).toBeInTheDocument();
    });
  });

  it('shows NG badge for NG image', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('NG', 'NG_1.png', 'analysis'),
    );
    renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('NG_1.png')] },
      });
    });
    await waitFor(() => {
      expect(screen.getByText('NG')).toBeInTheDocument();
    });
  });

  it('updates analysis count to 1 after upload', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => {
      expect(screen.getByTestId('analysis-count')).toHaveTextContent('1');
    });
  });
});

// ── Delete ────────────────────────────────────────────────────

describe('InputPanel — delete image', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls deleteImage with the image id when delete button is clicked', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis', 'img-abc'),
    );
    vi.mocked(api.deleteImage).mockResolvedValueOnce({ deleted: true });
    renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => expect(screen.getByText('OK_1.png')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('delete-img-abc'));
    });
    await waitFor(() => {
      expect(api.deleteImage).toHaveBeenCalledWith('img-abc');
    });
  });

  it('removes image from store after delete', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis', 'img-abc'),
    );
    vi.mocked(api.deleteImage).mockResolvedValueOnce({ deleted: true });
    const { store } = renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => expect(store.getState().images.analysis).toHaveLength(1));
    await act(async () => {
      fireEvent.click(screen.getByTestId('delete-img-abc'));
    });
    await waitFor(() => {
      expect(store.getState().images.analysis).toHaveLength(0);
    });
  });
});

// ── Clear All ─────────────────────────────────────────────────

describe('InputPanel — clear all', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls clearImages with purpose=analysis', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    vi.mocked(api.clearImages).mockResolvedValueOnce({ deleted_count: 1 });
    renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => expect(screen.getByText('OK_1.png')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('analysis-clear-btn'));
    });
    await waitFor(() => {
      expect(api.clearImages).toHaveBeenCalledWith('analysis');
    });
  });

  it('clears analysis images from store after Clear All', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    vi.mocked(api.clearImages).mockResolvedValueOnce({ deleted_count: 1 });
    const { store } = renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('analysis-file-input'), {
        target: { files: [makeFile('OK_1.png')] },
      });
    });
    await waitFor(() => expect(store.getState().images.analysis).toHaveLength(1));
    await act(async () => {
      fireEvent.click(screen.getByTestId('analysis-clear-btn'));
    });
    await waitFor(() => {
      expect(store.getState().images.analysis).toHaveLength(0);
    });
  });

  it('calls clearImages with purpose=test', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('NG', 'NG_1.png', 'test'),
    );
    vi.mocked(api.clearImages).mockResolvedValueOnce({ deleted_count: 1 });
    renderInputPanel();
    await act(async () => {
      fireEvent.change(screen.getByTestId('test-file-input'), {
        target: { files: [makeFile('NG_1.png')] },
      });
    });
    await waitFor(() => expect(screen.getByText('NG_1.png')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('test-clear-btn'));
    });
    await waitFor(() => {
      expect(api.clearImages).toHaveBeenCalledWith('test');
    });
  });
});

// ── Drag and drop ─────────────────────────────────────────────

describe('InputPanel — drag and drop', () => {
  beforeEach(() => vi.clearAllMocks());

  it('uploads valid file dropped on analysis zone', async () => {
    vi.mocked(api.uploadImage).mockResolvedValueOnce(
      makeApiImage('OK', 'OK_1.png', 'analysis'),
    );
    renderInputPanel();
    const zone = screen.getByTestId('analysis-drop-zone');
    const file = makeFile('OK_1.png');
    await act(async () => {
      fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    });
    await waitFor(() => {
      expect(api.uploadImage).toHaveBeenCalledWith(file, 'analysis');
    });
  });

  it('shows validation error on drop of invalid file', async () => {
    renderInputPanel();
    const zone = screen.getByTestId('analysis-drop-zone');
    await act(async () => {
      fireEvent.drop(zone, { dataTransfer: { files: [makeFile('bad_name.png')] } });
    });
    expect(screen.getByText(/invalid|OK_N|NG_N|filename/i)).toBeInTheDocument();
  });
});
