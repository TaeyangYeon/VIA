#!/usr/bin/env node
'use strict';

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

const FRONTEND_DIR = __dirname;
let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ ${name}`);
    console.error(`    ${err.message}`);
    failed++;
  }
}

console.log('\n=== Step 50: Electron 앱 시작 자동화 검증 ===\n');

// --- main.js: FastAPI 자동 시작 ---
console.log('[ main.js — FastAPI 자동 시작 ]');

test('main.js 가 유효한 JavaScript이다', () => {
  execSync(`node --check "${path.join(FRONTEND_DIR, 'main.js')}"`, { stdio: 'pipe' });
});

test('main.js 에 uvicorn 스폰 명령이 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('uvicorn'), 'uvicorn spawn command not found in main.js');
});

test('main.js 에 spawnBackend 또는 spawn 함수가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(
    src.includes('spawnBackend') || src.includes('spawn('),
    'backend spawn logic not found in main.js'
  );
});

test('main.js 에 .venv Python 경로 탐색 코드가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('.venv'), '.venv Python path detection not found in main.js');
});

test('main.js 에 포트 8000 설정이 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('8000'), 'port 8000 not found in main.js');
});

test('main.js 에 health 폴링 로직이 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(
    src.includes('health') && (src.includes('poll') || src.includes('retry') || src.includes('interval')),
    'health polling logic not found in main.js'
  );
});

test('main.js 에 30초 타임아웃 설정이 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(
    src.includes('30000') || src.includes('30 * 1000') || src.includes('maxAttempts'),
    'timeout configuration not found in main.js'
  );
});

test('main.js 에 백엔드 오류 다이얼로그 코드가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('dialog') || src.includes('showErrorBox'), 'error dialog code not found in main.js');
});

// --- main.js: 프로세스 정리 ---
console.log('\n[ main.js — 프로세스 정리 ]');

test('main.js 에 SIGTERM 코드가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('SIGTERM'), 'SIGTERM not found in main.js');
});

test('main.js 에 SIGKILL 코드가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('SIGKILL'), 'SIGKILL not found in main.js');
});

test('main.js 에 before-quit 또는 will-quit 이벤트 핸들러가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(
    src.includes('before-quit') || src.includes('will-quit'),
    'quit cleanup handler not found in main.js'
  );
});

test('main.js 에 백엔드 프로세스 참조 변수가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(
    src.includes('backendProcess') || src.includes('fastApiProcess') || src.includes('pythonProcess'),
    'backend process reference variable not found in main.js'
  );
});

// --- main.js: IPC 핸들러 ---
console.log('\n[ main.js — IPC 핸들러 ]');

test('main.js 에 via:getBackendStatus IPC 핸들러가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('via:getBackendStatus'), 'via:getBackendStatus IPC handler not found in main.js');
});

test('main.js 에 via:getEngineStatus IPC 핸들러가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('via:getEngineStatus'), 'via:getEngineStatus IPC handler not found in main.js');
});

// --- preload.js: IPC 채널 노출 ---
console.log('\n[ preload.js — IPC 채널 노출 ]');

test('preload.js 가 유효한 JavaScript이다', () => {
  execSync(`node --check "${path.join(FRONTEND_DIR, 'preload.js')}"`, { stdio: 'pipe' });
});

test('preload.js 에 getBackendStatus 가 노출된다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'preload.js'), 'utf8');
  assert.ok(src.includes('getBackendStatus'), 'getBackendStatus not exposed in preload.js');
});

test('preload.js 에 getEngineStatus 가 노출된다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'preload.js'), 'utf8');
  assert.ok(src.includes('getEngineStatus'), 'getEngineStatus not exposed in preload.js');
});

test('preload.js 에 via:getBackendStatus IPC 채널 사용이 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'preload.js'), 'utf8');
  assert.ok(src.includes('via:getBackendStatus'), 'via:getBackendStatus IPC channel not found in preload.js');
});

test('preload.js 에 via:getEngineStatus IPC 채널 사용이 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'preload.js'), 'utf8');
  assert.ok(src.includes('via:getEngineStatus'), 'via:getEngineStatus IPC channel not found in preload.js');
});

// --- OllamaSetupGuide 컴포넌트 파일 존재 확인 ---
console.log('\n[ OllamaSetupGuide 컴포넌트 ]');

test('OllamaSetupGuide.tsx 파일이 존재한다', () => {
  const componentPath = path.join(FRONTEND_DIR, 'src', 'components', 'OllamaSetupGuide.tsx');
  assert.ok(fs.existsSync(componentPath), 'OllamaSetupGuide.tsx not found');
});

test('OllamaSetupGuide.tsx 에 retry 기능이 있다', () => {
  const componentPath = path.join(FRONTEND_DIR, 'src', 'components', 'OllamaSetupGuide.tsx');
  if (!fs.existsSync(componentPath)) throw new Error('OllamaSetupGuide.tsx not found');
  const src = fs.readFileSync(componentPath, 'utf8');
  assert.ok(src.includes('onRetry') || src.includes('retry'), 'retry functionality not found');
});

test('OllamaSetupGuide.tsx 에 dismiss 기능이 있다', () => {
  const componentPath = path.join(FRONTEND_DIR, 'src', 'components', 'OllamaSetupGuide.tsx');
  if (!fs.existsSync(componentPath)) throw new Error('OllamaSetupGuide.tsx not found');
  const src = fs.readFileSync(componentPath, 'utf8');
  assert.ok(src.includes('onDismiss') || src.includes('dismiss'), 'dismiss functionality not found');
});

test('OllamaSetupGuide.tsx 에 ollama.ai 링크가 있다', () => {
  const componentPath = path.join(FRONTEND_DIR, 'src', 'components', 'OllamaSetupGuide.tsx');
  if (!fs.existsSync(componentPath)) throw new Error('OllamaSetupGuide.tsx not found');
  const src = fs.readFileSync(componentPath, 'utf8');
  assert.ok(src.includes('ollama.ai'), 'ollama.ai link not found');
});

test('OllamaSetupGuide.tsx 에 lucide-react 아이콘이 사용된다', () => {
  const componentPath = path.join(FRONTEND_DIR, 'src', 'components', 'OllamaSetupGuide.tsx');
  if (!fs.existsSync(componentPath)) throw new Error('OllamaSetupGuide.tsx not found');
  const src = fs.readFileSync(componentPath, 'utf8');
  assert.ok(src.includes('lucide-react'), 'lucide-react not used in OllamaSetupGuide.tsx');
});

// --- 결과 출력 ---
console.log(`\n=== 결과: ${passed} passed, ${failed} failed ===\n`);
if (failed > 0) {
  process.exit(1);
}
