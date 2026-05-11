import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import Layout from '../components/Layout';
import projectReducer from '../store/slices/projectSlice';
import imagesReducer from '../store/slices/imagesSlice';
import configReducer from '../store/slices/configSlice';
import directivesReducer from '../store/slices/directivesSlice';
import executionReducer from '../store/slices/executionSlice';
import resultReducer from '../store/slices/resultSlice';
import logsReducer from '../store/slices/logsSlice';

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

const renderLayout = () => {
  const store = createTestStore();
  const result = render(
    <Provider store={store}>
      <Layout />
    </Provider>,
  );
  return { ...result, store };
};

// ── Sidebar rendering ──────────────────────────────────────────

describe('Layout — sidebar rendering', () => {
  it('renders a navigation element', () => {
    renderLayout();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('renders Input nav item', () => {
    renderLayout();
    expect(screen.getByText('Input')).toBeInTheDocument();
  });

  it('renders Directive nav item', () => {
    renderLayout();
    expect(screen.getByText('Directive')).toBeInTheDocument();
  });

  it('renders Config nav item', () => {
    renderLayout();
    expect(screen.getByText('Config')).toBeInTheDocument();
  });

  it('renders Execution nav item', () => {
    renderLayout();
    expect(screen.getByText('Execution')).toBeInTheDocument();
  });

  it('renders Result nav item', () => {
    renderLayout();
    expect(screen.getByText('Result')).toBeInTheDocument();
  });

  it('renders Log nav item', () => {
    renderLayout();
    expect(screen.getByText('Log')).toBeInTheDocument();
  });
});

// ── Default active panel ───────────────────────────────────────

describe('Layout — default state', () => {
  it('shows Input panel content by default (Analysis Images section)', () => {
    renderLayout();
    expect(screen.getByText(/Analysis Images/i)).toBeInTheDocument();
  });

  it('Input nav item is marked active by default', () => {
    renderLayout();
    expect(screen.getByTestId('nav-Input')).toHaveAttribute('data-active', 'true');
  });

  it('other nav items are not active by default', () => {
    renderLayout();
    ['Directive', 'Config', 'Execution', 'Result', 'Log'].forEach((panel) => {
      expect(screen.getByTestId(`nav-${panel}`)).not.toHaveAttribute('data-active', 'true');
    });
  });
});

// ── Panel switching ────────────────────────────────────────────

describe('Layout — panel switching', () => {
  it('clicking Config nav hides Input panel content', () => {
    renderLayout();
    fireEvent.click(screen.getByText('Config'));
    expect(screen.queryByText(/Analysis Images/i)).not.toBeInTheDocument();
  });

  it('clicking Log nav hides Input panel content', () => {
    renderLayout();
    fireEvent.click(screen.getByText('Log'));
    expect(screen.queryByText(/Analysis Images/i)).not.toBeInTheDocument();
  });

  it('clicking a different panel and back to Input restores Input content', () => {
    renderLayout();
    fireEvent.click(screen.getByText('Execution'));
    fireEvent.click(screen.getByText('Input'));
    expect(screen.getByText(/Analysis Images/i)).toBeInTheDocument();
  });
});

// ── Active state management ────────────────────────────────────

describe('Layout — active state', () => {
  it('clicking Config marks Config nav as active', () => {
    renderLayout();
    fireEvent.click(screen.getByText('Config'));
    expect(screen.getByTestId('nav-Config')).toHaveAttribute('data-active', 'true');
  });

  it('clicking Config deactivates Input nav', () => {
    renderLayout();
    fireEvent.click(screen.getByText('Config'));
    expect(screen.getByTestId('nav-Input')).not.toHaveAttribute('data-active', 'true');
  });

  it('only one nav item is active at a time', () => {
    renderLayout();
    fireEvent.click(screen.getByText('Result'));
    const panels = ['Input', 'Directive', 'Config', 'Execution', 'Result', 'Log'];
    const activeItems = panels.filter(
      (p) => screen.getByTestId(`nav-${p}`).getAttribute('data-active') === 'true',
    );
    expect(activeItems).toHaveLength(1);
    expect(activeItems[0]).toBe('Result');
  });
});

// ── Workspace area ─────────────────────────────────────────────

describe('Layout — workspace', () => {
  it('renders a main content area', () => {
    renderLayout();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
