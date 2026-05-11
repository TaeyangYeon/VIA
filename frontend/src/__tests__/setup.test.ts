import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';

const root = resolve(__dirname, '../../');
const src = resolve(root, 'src');

describe('Step 33: Vite + React + TypeScript + TailwindCSS setup', () => {
  describe('Config files', () => {
    test('tsconfig.json exists and has strict mode', () => {
      const path = resolve(root, 'tsconfig.json');
      expect(existsSync(path)).toBe(true);
      const content = JSON.parse(readFileSync(path, 'utf-8'));
      expect(content.compilerOptions.strict).toBe(true);
    });

    test('tailwind.config.js exists', () => {
      expect(existsSync(resolve(root, 'tailwind.config.js'))).toBe(true);
    });

    test('postcss.config.js exists', () => {
      expect(existsSync(resolve(root, 'postcss.config.js'))).toBe(true);
    });

    test('vite.config.ts exists', () => {
      expect(existsSync(resolve(root, 'vite.config.ts'))).toBe(true);
    });

    test('index.html exists at frontend root', () => {
      expect(existsSync(resolve(root, 'index.html'))).toBe(true);
    });
  });

  describe('Source files', () => {
    test('App.tsx exists', () => {
      expect(existsSync(resolve(src, 'App.tsx'))).toBe(true);
    });

    test('main.tsx exists', () => {
      expect(existsSync(resolve(src, 'main.tsx'))).toBe(true);
    });

    test('index.css exists', () => {
      expect(existsSync(resolve(src, 'index.css'))).toBe(true);
    });

    test('vite-env.d.ts exists', () => {
      expect(existsSync(resolve(src, 'vite-env.d.ts'))).toBe(true);
    });

    test('design-tokens.ts exists', () => {
      expect(existsSync(resolve(src, 'styles/design-tokens.ts'))).toBe(true);
    });
  });

  describe('design-tokens.ts exports', () => {
    test('exports all background color constants', async () => {
      const tokens = await import('../styles/design-tokens');
      expect(tokens.bg_primary).toBe('#0a0a0a');
      expect(tokens.bg_card).toBe('#111111');
      expect(tokens.bg_secondary).toBe('#1a1a1a');
      expect(tokens.bg_hover).toBe('#222222');
    });

    test('exports all border color constants', async () => {
      const tokens = await import('../styles/design-tokens');
      expect(tokens.border_default).toBe('#2a2a2a');
      expect(tokens.border_emphasis).toBe('#3a3a3a');
    });

    test('exports all text color constants', async () => {
      const tokens = await import('../styles/design-tokens');
      expect(tokens.text_primary).toBe('#f5f5f5');
      expect(tokens.text_secondary).toBe('#a0a0a0');
      expect(tokens.text_disabled).toBe('#555555');
    });

    test('exports all accent color constants', async () => {
      const tokens = await import('../styles/design-tokens');
      expect(tokens.accent_action).toBe('#ffffff');
      expect(tokens.accent_success).toBe('#4ade80');
      expect(tokens.accent_warning).toBe('#facc15');
      expect(tokens.accent_error).toBe('#f87171');
      expect(tokens.accent_info).toBe('#60a5fa');
    });

    test('exports font and spacing constants', async () => {
      const tokens = await import('../styles/design-tokens');
      expect(tokens.font_sans).toContain('Inter');
      expect(tokens.font_mono).toContain('JetBrains Mono');
      expect(tokens.spacing).toBeDefined();
    });
  });

  describe('package.json dependencies', () => {
    test('has required runtime dependencies', () => {
      const pkg = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf-8'));
      const deps = { ...pkg.dependencies, ...pkg.devDependencies };
      expect(deps['react']).toBeDefined();
      expect(deps['react-dom']).toBeDefined();
      expect(deps['lucide-react']).toBeDefined();
    });

    test('has required dev dependencies', () => {
      const pkg = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf-8'));
      const deps = { ...pkg.dependencies, ...pkg.devDependencies };
      expect(deps['typescript']).toBeDefined();
      expect(deps['tailwindcss']).toBeDefined();
      expect(deps['vite']).toBeDefined();
      expect(deps['@vitejs/plugin-react']).toBeDefined();
      expect(deps['vitest']).toBeDefined();
    });
  });
});
