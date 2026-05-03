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

console.log('\n=== Step 32: Electron 프로젝트 초기화 검증 ===\n');

// --- package.json 검증 ---
console.log('[ package.json ]');
test('package.json 파일이 존재한다', () => {
  const pkg = path.join(FRONTEND_DIR, 'package.json');
  assert.ok(fs.existsSync(pkg), 'package.json not found');
});

test('name 필드가 "via-frontend"이다', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf8'));
  assert.strictEqual(pkg.name, 'via-frontend');
});

test('version 필드가 존재한다', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf8'));
  assert.ok(pkg.version, 'version field missing');
});

test('main 필드가 "main.js"를 가리킨다', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf8'));
  assert.strictEqual(pkg.main, 'main.js');
});

test('scripts.start 가 존재한다', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf8'));
  assert.ok(pkg.scripts && pkg.scripts.start, 'scripts.start missing');
});

test('scripts.build 가 존재한다', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf8'));
  assert.ok(pkg.scripts && pkg.scripts.build, 'scripts.build missing');
});

test('scripts.test 가 존재한다', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf8'));
  assert.ok(pkg.scripts && pkg.scripts.test, 'scripts.test missing');
});

test('devDependencies에 electron이 있다', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf8'));
  assert.ok(
    (pkg.devDependencies && pkg.devDependencies.electron) ||
    (pkg.dependencies && pkg.dependencies.electron),
    'electron not in dependencies'
  );
});

test('devDependencies에 electron-builder가 있다', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf8'));
  assert.ok(
    (pkg.devDependencies && pkg.devDependencies['electron-builder']) ||
    (pkg.dependencies && pkg.dependencies['electron-builder']),
    'electron-builder not in dependencies'
  );
});

// --- main.js 검증 ---
console.log('\n[ main.js ]');
test('main.js 파일이 존재한다', () => {
  assert.ok(fs.existsSync(path.join(FRONTEND_DIR, 'main.js')), 'main.js not found');
});

test('main.js 가 유효한 JavaScript이다 (구문 검사)', () => {
  const mainPath = path.join(FRONTEND_DIR, 'main.js');
  execSync(`node --check "${mainPath}"`, { stdio: 'pipe' });
});

test('main.js 에 BrowserWindow 생성 코드가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('BrowserWindow'), 'BrowserWindow not found in main.js');
});

test('main.js 에 1400x900 윈도우 크기가 설정되어 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('1400'), 'width 1400 not found');
  assert.ok(src.includes('900'), 'height 900 not found');
});

test('main.js 에 배경색 #0a0a0a가 설정되어 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('#0a0a0a'), 'backgroundColor #0a0a0a not found');
});

test('main.js 에 VIA 타이틀이 설정되어 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('VIA'), 'window title not found');
});

test('main.js 에 nodeIntegration: false가 설정되어 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('nodeIntegration') && src.includes('false'), 'nodeIntegration: false not found');
});

test('main.js 에 contextIsolation: true가 설정되어 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('contextIsolation') && src.includes('true'), 'contextIsolation: true not found');
});

test('main.js 에 preload 경로가 설정되어 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('preload'), 'preload not found in main.js');
});

test('main.js 에 localhost:5173 (Vite dev server) 로드 코드가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('5173') || src.includes('localhost'), 'dev server URL not found');
});

test('main.js 에 window-all-closed 이벤트 핸들러가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('window-all-closed'), 'window-all-closed handler not found');
});

test('main.js 에 activate 이벤트 핸들러가 있다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'main.js'), 'utf8');
  assert.ok(src.includes('activate'), 'activate handler not found');
});

// --- preload.js 검증 ---
console.log('\n[ preload.js ]');
test('preload.js 파일이 존재한다', () => {
  assert.ok(fs.existsSync(path.join(FRONTEND_DIR, 'preload.js')), 'preload.js not found');
});

test('preload.js 가 유효한 JavaScript이다 (구문 검사)', () => {
  const preloadPath = path.join(FRONTEND_DIR, 'preload.js');
  execSync(`node --check "${preloadPath}"`, { stdio: 'pipe' });
});

test('preload.js 에 contextBridge가 사용된다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'preload.js'), 'utf8');
  assert.ok(src.includes('contextBridge'), 'contextBridge not found in preload.js');
});

test('preload.js 에 window.via API가 노출된다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'preload.js'), 'utf8');
  assert.ok(src.includes('via'), '"via" namespace not found in preload.js');
});

test('preload.js 에 platform 정보가 포함된다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'preload.js'), 'utf8');
  assert.ok(src.includes('platform'), 'platform not exposed in preload.js');
});

test('preload.js 에 versions 정보가 포함된다', () => {
  const src = fs.readFileSync(path.join(FRONTEND_DIR, 'preload.js'), 'utf8');
  assert.ok(src.includes('versions'), 'versions not exposed in preload.js');
});

// --- npm 패키지 설치 검증 ---
console.log('\n[ npm 패키지 설치 확인 ]');
test('electron 패키지가 설치되어 있다 (node_modules)', () => {
  const electronPath = path.join(FRONTEND_DIR, 'node_modules', 'electron');
  assert.ok(fs.existsSync(electronPath), 'electron not installed in node_modules');
});

test('electron-builder 패키지가 설치되어 있다 (node_modules)', () => {
  const ebPath = path.join(FRONTEND_DIR, 'node_modules', 'electron-builder');
  assert.ok(fs.existsSync(ebPath), 'electron-builder not installed in node_modules');
});

// --- 결과 출력 ---
console.log(`\n=== 결과: ${passed} passed, ${failed} failed ===\n`);
if (failed > 0) {
  process.exit(1);
}
