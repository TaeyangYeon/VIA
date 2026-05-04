import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import PipelineViewer from '../components/PipelineViewer';

const SAMPLE_PIPELINE = {
  pipeline_id: 'p1',
  name: 'Test Pipeline',
  blocks: [
    { name: 'GaussianBlur', category: 'noise_reduction', params: { ksize: 5 } },
    { name: 'Threshold', category: 'threshold', params: { value: 128 } },
    { name: 'Canny', category: 'edge', params: { low: 50, high: 150 } },
  ],
  score: 0.95,
};

// ── Empty state ────────────────────────────────────────────────

describe('PipelineViewer — empty state', () => {
  it('shows pipeline-empty when pipeline is null', () => {
    render(<PipelineViewer pipeline={null} />);
    expect(screen.getByTestId('pipeline-empty')).toBeInTheDocument();
  });

  it('shows pipeline-empty when pipeline has no blocks', () => {
    render(<PipelineViewer pipeline={{ ...SAMPLE_PIPELINE, blocks: [] }} />);
    expect(screen.getByTestId('pipeline-empty')).toBeInTheDocument();
  });

  it('does not render pipeline-viewer when empty', () => {
    render(<PipelineViewer pipeline={null} />);
    expect(screen.queryByTestId('pipeline-viewer')).not.toBeInTheDocument();
  });
});

// ── Block rendering ────────────────────────────────────────────

describe('PipelineViewer — block rendering', () => {
  it('renders pipeline-viewer wrapper', () => {
    render(<PipelineViewer pipeline={SAMPLE_PIPELINE} />);
    expect(screen.getByTestId('pipeline-viewer')).toBeInTheDocument();
  });

  it('renders a block card for each block', () => {
    render(<PipelineViewer pipeline={SAMPLE_PIPELINE} />);
    expect(screen.getByTestId('pipeline-block-0')).toBeInTheDocument();
    expect(screen.getByTestId('pipeline-block-1')).toBeInTheDocument();
    expect(screen.getByTestId('pipeline-block-2')).toBeInTheDocument();
  });

  it('shows block name in first card', () => {
    render(<PipelineViewer pipeline={SAMPLE_PIPELINE} />);
    expect(screen.getByTestId('pipeline-block-0').textContent).toContain('GaussianBlur');
  });

  it('shows block name in second card', () => {
    render(<PipelineViewer pipeline={SAMPLE_PIPELINE} />);
    expect(screen.getByTestId('pipeline-block-1').textContent).toContain('Threshold');
  });

  it('shows category badge on each block card', () => {
    render(<PipelineViewer pipeline={SAMPLE_PIPELINE} />);
    expect(screen.getByTestId('pipeline-category-badge-0').textContent).toContain('noise_reduction');
    expect(screen.getByTestId('pipeline-category-badge-1').textContent).toContain('threshold');
    expect(screen.getByTestId('pipeline-category-badge-2').textContent).toContain('edge');
  });

  it('shows params key=value in block card', () => {
    render(<PipelineViewer pipeline={SAMPLE_PIPELINE} />);
    expect(screen.getByTestId('pipeline-block-0').textContent).toContain('ksize');
  });
});

// ── Category badge colors ──────────────────────────────────────

describe('PipelineViewer — all category types render', () => {
  const categories = [
    { name: 'ColorConvert', category: 'color_space' },
    { name: 'Denoise', category: 'noise_reduction' },
    { name: 'Thresh', category: 'threshold' },
    { name: 'Dilate', category: 'morphology' },
    { name: 'EdgeDet', category: 'edge' },
  ];

  it.each(categories)('renders $category category badge', ({ name, category }) => {
    const pipeline = { ...SAMPLE_PIPELINE, blocks: [{ name, category, params: {} }] };
    render(<PipelineViewer pipeline={pipeline} />);
    expect(screen.getByTestId('pipeline-category-badge-0').textContent).toContain(category);
  });
});
