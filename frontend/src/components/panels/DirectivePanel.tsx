import React, { useState, useEffect } from 'react';
import {
  Brain,
  Eye,
  Layers,
  Target,
  ClipboardList,
  Code2,
  TestTube2,
  ChevronDown,
  ChevronRight,
  Save,
  RotateCcw,
  Check,
  Settings2,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import {
  selectDirectives,
  setDirective,
  setAllDirectives,
  resetDirectives as resetDirectivesAction,
} from '../../store/slices/directivesSlice';
import * as api from '../../services/api';
import {
  bg_secondary,
  border_default,
  border_emphasis,
  text_primary,
  text_secondary,
  text_disabled,
  accent_success,
  accent_error,
  font_mono,
} from '../../styles/design-tokens';

type AgentKey =
  | 'orchestrator'
  | 'spec'
  | 'image_analysis'
  | 'pipeline_composer'
  | 'vision_judge'
  | 'inspection_plan'
  | 'algorithm_coder'
  | 'test';

interface AgentDef {
  key: AgentKey;
  koreanName: string;
  description: string;
  icon: React.ReactNode;
}

const AGENTS: AgentDef[] = [
  {
    key: 'orchestrator',
    koreanName: '오케스트레이터',
    description: '전체 실행 전략 및 목표 우선순위 지시',
    icon: <Brain size={14} />,
  },
  {
    key: 'spec',
    koreanName: '스펙 에이전트',
    description: '목적/모드/성공기준 해석 방향 지시',
    icon: <Target size={14} />,
  },
  {
    key: 'image_analysis',
    koreanName: '이미지 분석',
    description: '이미지 특성 분석 시 집중할 요소 지시',
    icon: <Eye size={14} />,
  },
  {
    key: 'pipeline_composer',
    koreanName: '파이프라인 구성',
    description: '파이프라인 조합 전략 및 우선 블록 지시',
    icon: <Layers size={14} />,
  },
  {
    key: 'vision_judge',
    koreanName: '비전 판정',
    description: '처리 결과 시각적 판단 기준 지시',
    icon: <Settings2 size={14} />,
  },
  {
    key: 'inspection_plan',
    koreanName: '검사 설계',
    description: '검사 항목 구성 방향 및 필수 포함 항목 지시',
    icon: <ClipboardList size={14} />,
  },
  {
    key: 'algorithm_coder',
    koreanName: '알고리즘 코더',
    description: '코드 생성 시 선호하는 기법/제약 지시',
    icon: <Code2 size={14} />,
  },
  {
    key: 'test',
    koreanName: '테스트 에이전트',
    description: '테스트 평가 시 가중치/엄격도 지시',
    icon: <TestTube2 size={14} />,
  },
];

type SaveStatus = 'idle' | 'saving' | 'success' | 'error';

export default function DirectivePanel() {
  const dispatch = useAppDispatch();
  const directives = useAppSelector(selectDirectives);

  const [expandedKey, setExpandedKey] = useState<AgentKey | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [resetError, setResetError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDirectives()
      .then((data) => {
        dispatch(setAllDirectives(data));
        setIsLoading(false);
      })
      .catch(() => {
        setLoadError('불러오기 실패');
        setIsLoading(false);
      });
  }, [dispatch]);

  const handleCardClick = (key: AgentKey) => {
    setExpandedKey((prev) => (prev === key ? null : key));
  };

  const handleChange = (key: AgentKey, value: string) => {
    dispatch(setDirective({ key, value: value || null }));
  };

  const handleSaveAll = async () => {
    setSaveStatus('saving');
    setResetError(null);
    try {
      await api.saveDirectives(directives);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch {
      setSaveStatus('error');
    }
  };

  const handleResetAll = async () => {
    setSaveStatus('idle');
    setResetError(null);
    try {
      await api.resetDirectives();
      dispatch(resetDirectivesAction());
    } catch {
      setResetError('초기화 실패');
    }
  };

  const allEmpty = Object.values(directives).every((v) => v === null);

  if (isLoading) {
    return (
      <div
        data-testid="directives-loading"
        className="flex items-center justify-center h-full"
      >
        <p className="text-sm" style={{ color: text_secondary }}>
          불러오는 중...
        </p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div
        data-testid="load-error"
        className="flex items-center justify-center h-full"
      >
        <p className="text-sm" style={{ color: accent_error }}>
          {loadError}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b shrink-0"
        style={{ borderColor: border_default }}
      >
        <span className="text-sm font-medium" style={{ color: text_primary }}>
          에이전트 지시문
        </span>

        <div className="flex items-center gap-2">
          {saveStatus === 'saving' && (
            <span className="text-xs" style={{ color: text_secondary }}>
              저장 중...
            </span>
          )}
          {saveStatus === 'success' && (
            <span
              data-testid="save-success"
              className="flex items-center gap-1 text-xs"
              style={{ color: accent_success }}
            >
              <Check size={11} />
              저장됨
            </span>
          )}
          {saveStatus === 'error' && (
            <span
              data-testid="save-error"
              className="text-xs"
              style={{ color: accent_error }}
            >
              저장 실패
            </span>
          )}
          {resetError && (
            <span
              data-testid="reset-error"
              className="text-xs"
              style={{ color: accent_error }}
            >
              {resetError}
            </span>
          )}

          <button
            data-testid="reset-all-btn"
            onClick={handleResetAll}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-all duration-150"
            style={{ color: text_secondary, backgroundColor: bg_secondary }}
          >
            <RotateCcw size={11} />
            초기화
          </button>

          <button
            data-testid="save-all-btn"
            onClick={handleSaveAll}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-all duration-150"
            style={{ color: text_primary, backgroundColor: bg_secondary }}
          >
            <Save size={11} />
            저장
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {allEmpty && (
          <div
            data-testid="empty-state"
            className="px-3 py-2 rounded text-xs"
            style={{ color: text_disabled, backgroundColor: bg_secondary }}
          >
            설정된 지시문이 없습니다. 에이전트가 자율적으로 판단합니다.
          </div>
        )}

        {AGENTS.map(({ key, koreanName, description, icon }) => {
          const isExpanded = expandedKey === key;
          const value = directives[key];
          const hasDirective = value !== null && value !== '';

          return (
            <div
              key={key}
              className="rounded border backdrop-blur-sm"
              style={{
                backgroundColor: 'rgba(255,255,255,0.05)',
                borderColor: border_default,
              }}
            >
              {/* Card header (always visible) */}
              <button
                data-testid={`card-${key}`}
                onClick={() => handleCardClick(key)}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-all duration-150"
              >
                <span style={{ color: text_secondary }}>{icon}</span>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className="text-sm font-medium"
                      style={{ color: text_primary }}
                    >
                      {koreanName}
                    </span>
                    <span
                      className="text-xs"
                      style={{ color: text_disabled, fontFamily: font_mono }}
                    >
                      {key}
                    </span>
                    {hasDirective && (
                      <span
                        data-testid={`indicator-${key}`}
                        className="w-1.5 h-1.5 rounded-full shrink-0"
                        style={{ backgroundColor: accent_success }}
                      />
                    )}
                  </div>

                  <p
                    className="text-xs mt-0.5 truncate"
                    style={{ color: text_secondary }}
                  >
                    {description}
                  </p>

                  {/* Collapsed preview */}
                  {!isExpanded && hasDirective && (
                    <p
                      data-testid={`preview-${key}`}
                      className="text-xs mt-1 truncate"
                      style={{ color: text_disabled }}
                    >
                      {value!.length > 50 ? value!.slice(0, 50) + '…' : value}
                    </p>
                  )}
                </div>

                <span style={{ color: text_disabled }}>
                  {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                </span>
              </button>

              {/* Textarea — only when expanded */}
              {isExpanded && (
                <div className="px-3 pb-3">
                  <textarea
                    data-testid={`textarea-${key}`}
                    value={value ?? ''}
                    onChange={(e) => handleChange(key, e.target.value)}
                    placeholder="에이전트가 자동으로 판단합니다..."
                    rows={4}
                    className="w-full resize-none rounded px-2.5 py-2 text-xs outline-none transition-all duration-150"
                    style={{
                      backgroundColor: bg_secondary,
                      border: `1px solid ${border_emphasis}`,
                      color: text_primary,
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
