import React from 'react';
import { useAppSelector } from '../../store/hooks';
import { selectResult } from '../../store/slices/resultSlice';

export default function DebugResultButton() {
  const result = useAppSelector(selectResult);

  const handleClick = () => {
    // eslint-disable-next-line no-console
    console.log('=== [DEBUG] Redux result slice state ===');
    // eslint-disable-next-line no-console
    console.log(JSON.stringify(result, null, 2));

    const lines = Object.entries(result).map(([k, v]) => {
      if (v === null) return `${k}: null`;
      if (v === undefined) return `${k}: undefined`;
      if (typeof v === 'string') return `${k}: "${v.substring(0, 60)}"`;
      if (Array.isArray(v)) return `${k}: Array[${v.length}]`;
      if (typeof v === 'object') return `${k}: {${Object.keys(v).slice(0, 4).join(', ')}}`;
      return `${k}: ${String(v).substring(0, 60)}`;
    });

    const summaryNull = result.summary === null || result.summary === undefined || result.summary === '';
    const diagnosis = summaryNull
      ? '\n\n⚠ BUG: result.summary is falsy → ResultPanel shows empty state.\nsetResult was never dispatched or was dispatched with null values.'
      : '\n\n✓ result.summary is set — Redux state is populated correctly.\nIf ResultPanel still shows empty, check component re-render.';

    alert(
      '=== Redux result slice ===\n\n' +
      lines.join('\n') +
      diagnosis
    );
  };

  return (
    <button
      onClick={handleClick}
      style={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        zIndex: 9999,
        padding: '8px 14px',
        background: '#ef4444',
        color: '#fff',
        border: 'none',
        borderRadius: 6,
        fontSize: 11,
        fontFamily: 'monospace',
        cursor: 'pointer',
        boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
      }}
    >
      Debug Result
    </button>
  );
}
