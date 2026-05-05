import React, { useState } from 'react';
import {
  Upload,
  Settings,
  Play,
  BarChart2,
  FileText,
  ScrollText,
  Cpu,
  ChevronRight,
} from 'lucide-react';
import {
  bg_card,
  bg_secondary,
  border_default,
  text_primary,
  text_secondary,
} from '../styles/design-tokens';
import InputPanel from './panels/InputPanel';
import DirectivePanel from './panels/DirectivePanel';
import ConfigPanel from './panels/ConfigPanel';
import EngineSettingsPanel from './panels/EngineSettingsPanel';
import ExecutionPanel from './panels/ExecutionPanel';
import ResultPanel from './panels/ResultPanel';
import LogPanel from './panels/LogPanel';

type PanelName = 'Input' | 'Directive' | 'Config' | 'Engine' | 'Execution' | 'Result' | 'Log';

const PANELS: PanelName[] = ['Input', 'Directive', 'Config', 'Engine', 'Execution', 'Result', 'Log'];

const PANEL_ICONS: Record<PanelName, React.ReactNode> = {
  Input: <Upload size={15} />,
  Directive: <FileText size={15} />,
  Config: <Settings size={15} />,
  Engine: <Cpu size={15} />,
  Execution: <Play size={15} />,
  Result: <BarChart2 size={15} />,
  Log: <ScrollText size={15} />,
};

function PlaceholderPanel({ name }: { name: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <p className="text-sm" style={{ color: text_secondary }}>
        {name} panel — coming soon
      </p>
    </div>
  );
}

export default function Layout() {
  const [activePanel, setActivePanel] = useState<PanelName>('Input');

  const renderPanel = () => {
    if (activePanel === 'Input') return <InputPanel />;
    if (activePanel === 'Directive') return <DirectivePanel />;
    if (activePanel === 'Config') return <ConfigPanel />;
    if (activePanel === 'Engine') return <EngineSettingsPanel />;
    if (activePanel === 'Execution') return <ExecutionPanel />;
    if (activePanel === 'Result') return <ResultPanel />;
    if (activePanel === 'Log') return <LogPanel />;
    return <PlaceholderPanel name={activePanel} />;
  };

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#0a0a0a' }}>
      {/* Sidebar */}
      <nav
        className="flex flex-col w-44 shrink-0 border-r"
        style={{ backgroundColor: bg_card, borderColor: border_default }}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-2 px-4 py-4 border-b"
          style={{ borderColor: border_default }}
        >
          <Cpu size={16} style={{ color: text_primary }} strokeWidth={1.5} />
          <span className="text-sm font-semibold tracking-wide" style={{ color: text_primary }}>
            VIA
          </span>
        </div>

        {/* Nav items */}
        <div className="flex flex-col py-1.5">
          {PANELS.map((panel) => {
            const isActive = panel === activePanel;
            return (
              <button
                key={panel}
                data-testid={`nav-${panel}`}
                data-active={isActive ? 'true' : 'false'}
                onClick={() => setActivePanel(panel)}
                className="flex items-center gap-2.5 px-4 py-2 text-sm transition-all duration-150 text-left w-full"
                style={{
                  color: isActive ? text_primary : text_secondary,
                  backgroundColor: isActive ? bg_secondary : 'transparent',
                }}
              >
                {PANEL_ICONS[panel]}
                <span className="flex-1">{panel}</span>
                {isActive && (
                  <ChevronRight size={11} style={{ color: text_secondary }} />
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Main workspace */}
      <main className="flex-1 overflow-hidden">{renderPanel()}</main>
    </div>
  );
}
