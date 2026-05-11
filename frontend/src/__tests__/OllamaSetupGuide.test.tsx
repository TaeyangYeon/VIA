import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import OllamaSetupGuide from '../components/OllamaSetupGuide';

describe('OllamaSetupGuide — 렌더링', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />,
    );
    expect(container).toBeInTheDocument();
  });

  it('shows AI engine unavailable heading', () => {
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />);
    expect(screen.getByText(/AI Engine Not Available/i)).toBeInTheDocument();
  });

  it('shows step 1 install Ollama label', () => {
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />);
    expect(screen.getByText('Install Ollama')).toBeInTheDocument();
  });

  it('shows ollama serve instruction', () => {
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />);
    expect(screen.getByText(/ollama serve/i)).toBeInTheDocument();
  });

  it('shows ollama pull instruction', () => {
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />);
    expect(screen.getByText(/ollama pull/i)).toBeInTheDocument();
  });

  it('shows ollama.ai link', () => {
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />);
    const link = screen.getByRole('link', { name: /ollama\.ai/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', expect.stringContaining('ollama.ai'));
  });
});

describe('OllamaSetupGuide — 상호작용', () => {
  it('renders Retry Connection button', () => {
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />);
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('calls onRetry when Retry Connection button is clicked', () => {
    const onRetry = vi.fn();
    render(<OllamaSetupGuide onRetry={onRetry} onDismiss={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('renders dismiss / continue without AI button', () => {
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />);
    expect(screen.getByText(/continue without/i)).toBeInTheDocument();
  });

  it('calls onDismiss when continue-without button is clicked', () => {
    const onDismiss = vi.fn();
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByText(/continue without/i));
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});

describe('OllamaSetupGuide — 디자인 시스템', () => {
  it('renders as a fixed overlay', () => {
    const { container } = render(
      <OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />,
    );
    const overlay = container.querySelector('.fixed');
    expect(overlay).toBeInTheDocument();
  });

  it('shows limited functionality warning', () => {
    render(<OllamaSetupGuide onRetry={() => {}} onDismiss={() => {}} />);
    expect(screen.getByText(/limited/i)).toBeInTheDocument();
  });
});
