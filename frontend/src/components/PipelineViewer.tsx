import React from 'react';
import { GitBranch } from 'lucide-react';
import {
  border_default,
  text_primary,
  text_secondary,
  accent_info,
  accent_success,
  accent_warning,
  accent_error,
  font_mono,
} from '../styles/design-tokens';

interface PipelineBlock {
  name: string;
  category: string;
  params: Record<string, unknown>;
}

interface Pipeline {
  pipeline_id: string;
  name: string;
  blocks: PipelineBlock[];
  score: number;
}

interface PipelineViewerProps {
  pipeline: Pipeline | null;
}

const CATEGORY_COLORS: Record<string, string> = {
  color_space: accent_info,
  noise_reduction: accent_success,
  threshold: accent_warning,
  morphology: '#c084fc',
  edge: accent_error,
};

function categoryColor(category: string): string {
  return CATEGORY_COLORS[category] ?? text_secondary;
}

export default function PipelineViewer({ pipeline }: PipelineViewerProps) {
  if (!pipeline || pipeline.blocks.length === 0) {
    return (
      <div
        data-testid="pipeline-empty"
        className="flex flex-col items-center justify-center gap-2 py-8"
        style={{ color: text_secondary }}
      >
        <GitBranch size={24} strokeWidth={1.5} />
        <span className="text-xs">No pipeline data</span>
      </div>
    );
  }

  return (
    <div data-testid="pipeline-viewer" className="overflow-x-auto">
      <div className="flex items-center min-w-max py-2">
        {pipeline.blocks.map((block, i) => {
          const color = categoryColor(block.category);
          const params = Object.entries(block.params ?? {});

          return (
            <React.Fragment key={i}>
              {/* Block card */}
              <div
                data-testid={`pipeline-block-${i}`}
                className="flex flex-col gap-2 p-3 rounded border bg-white/5 backdrop-blur-sm min-w-28 max-w-40 shrink-0 transition-all duration-150"
                style={{ borderColor: border_default }}
              >
                <span
                  className="text-xs font-semibold leading-tight truncate"
                  style={{ color: text_primary }}
                >
                  {block.name}
                </span>
                <span
                  data-testid={`pipeline-category-badge-${i}`}
                  className="self-start px-1.5 py-0.5 text-xs rounded"
                  style={{
                    color,
                    backgroundColor: `${color}20`,
                    border: `1px solid ${color}40`,
                  }}
                >
                  {block.category}
                </span>
                {params.length > 0 && (
                  <div className="flex flex-col gap-0.5">
                    {params.map(([k, v]) => (
                      <span
                        key={k}
                        className="text-xs truncate"
                        style={{ color: text_secondary, fontFamily: font_mono }}
                      >
                        {k}={String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Arrow connector */}
              {i < pipeline.blocks.length - 1 && (
                <div
                  className="flex items-center px-2 shrink-0 text-sm select-none"
                  style={{ color: text_secondary }}
                >
                  →
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
