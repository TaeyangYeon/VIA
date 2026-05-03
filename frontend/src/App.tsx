import { Cpu } from 'lucide-react';
import { bg_primary, text_primary, text_secondary } from './styles/design-tokens';

export default function App() {
  return (
    <div
      className="flex items-center justify-center min-h-screen"
      style={{ backgroundColor: bg_primary }}
    >
      <div className="flex flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-3">
          <Cpu
            className="transition-all duration-150"
            style={{ color: text_primary }}
            size={48}
            strokeWidth={1.5}
          />
          <h1
            className="text-4xl font-semibold tracking-tight"
            style={{ color: text_primary }}
          >
            VIA
          </h1>
          <p
            className="text-sm font-medium tracking-widest uppercase"
            style={{ color: text_secondary }}
          >
            Vision Intelligence Agent
          </p>
        </div>

        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg px-8 py-5 flex items-center gap-3">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-white/40 animate-pulse"
                style={{ animationDelay: `${i * 200}ms` }}
              />
            ))}
          </div>
          <span
            className="text-sm font-mono"
            style={{ color: text_secondary }}
          >
            System Initializing...
          </span>
        </div>
      </div>
    </div>
  );
}
