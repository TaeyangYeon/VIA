'use strict';
// Step 51: Packaging config validation tests
// Run with: node test_step51.js
// Does NOT invoke electron-builder (too slow / requires signing)

const fs = require('fs');
const path = require('path');

const FRONTEND = __dirname;
const PROJECT_ROOT = path.join(__dirname, '..');

let passed = 0;
let failed = 0;
const errors = [];

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ ${message}`);
    failed++;
    errors.push(message);
  }
}

function section(title) {
  console.log(`\n=== ${title} ===`);
}

// ── PNG dimension reader (no external deps) ──────────────────────────────────
function readPngDimensions(filePath) {
  const buf = fs.readFileSync(filePath);
  // PNG signature: 8 bytes; IHDR chunk starts at offset 8
  // Width at offset 16, Height at offset 20 (each 4 bytes big-endian)
  const PNG_SIG = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  for (let i = 0; i < 8; i++) {
    if (buf[i] !== PNG_SIG[i]) throw new Error('Not a valid PNG');
  }
  const width = buf.readUInt32BE(16);
  const height = buf.readUInt32BE(20);
  return { width, height };
}

// ── YAML structure validator (uses js-yaml) ──────────────────────────────────
let yaml;
try {
  yaml = require('js-yaml');
} catch {
  yaml = null;
}

function loadYaml(filePath) {
  if (!yaml) throw new Error('js-yaml not available');
  return yaml.load(fs.readFileSync(filePath, 'utf8'));
}

// ── Test sections ────────────────────────────────────────────────────────────

function testElectronBuilderYml() {
  section('electron-builder.yml');
  const ymlPath = path.join(FRONTEND, 'electron-builder.yml');
  assert(fs.existsSync(ymlPath), 'electron-builder.yml exists');
  if (!fs.existsSync(ymlPath)) return;

  let cfg;
  try {
    cfg = loadYaml(ymlPath);
    assert(true, 'electron-builder.yml is valid YAML');
  } catch (e) {
    assert(false, `electron-builder.yml is valid YAML (${e.message})`);
    return;
  }

  // App metadata
  assert(cfg.appId === 'com.via.desktop', 'appId is "com.via.desktop"');
  assert(cfg.productName === 'VIA', 'productName is "VIA"');
  assert(typeof cfg.copyright === 'string' && cfg.copyright.length > 0, 'copyright is set');

  // asar
  assert(cfg.asar === true, 'asar is true');

  // files includes main.js, preload.js, dist/**
  const files = cfg.files || [];
  assert(files.some(f => f === 'main.js' || (typeof f === 'object' && f.from === 'main.js')), 'files includes main.js');
  assert(files.some(f => f === 'preload.js' || (typeof f === 'object' && f.from === 'preload.js')), 'files includes preload.js');
  assert(files.some(f => typeof f === 'string' && f.includes('dist')), 'files includes dist/**');

  // extraResources includes backend/ and agents/
  const extra = cfg.extraResources || [];
  const hasBackend = extra.some(r => {
    if (typeof r === 'string') return r.includes('backend');
    if (typeof r === 'object') return (r.from || '').includes('backend') || (r.filter || []).some(f => f.includes('backend'));
    return false;
  });
  const hasAgents = extra.some(r => {
    if (typeof r === 'string') return r.includes('agents');
    if (typeof r === 'object') return (r.from || '').includes('agents') || (r.filter || []).some(f => f.includes('agents'));
    return false;
  });
  assert(hasBackend, 'extraResources includes backend/ directory');
  assert(hasAgents, 'extraResources includes agents/ directory');

  // macOS target
  const mac = cfg.mac || {};
  assert(
    Array.isArray(mac.target)
      ? mac.target.some(t => (typeof t === 'string' ? t : t.target) === 'dmg')
      : (mac.target === 'dmg' || (typeof mac.target === 'object' && mac.target.target === 'dmg')),
    'mac target includes dmg',
  );

  // electron-builder 25.x: arch must be inside mac.target[].arch, NOT as mac.arch top-level
  assert(
    mac.arch === undefined || mac.arch === null,
    'mac.arch is NOT set at top-level (electron-builder 25.x rejects this property)',
  );
  const dmgTarget = Array.isArray(mac.target)
    ? mac.target.find(t => typeof t === 'object' && t.target === 'dmg')
    : null;
  const targetArch = dmgTarget ? (dmgTarget.arch || []) : [];
  assert(targetArch.includes('x64'), 'mac target[dmg].arch includes x64 (Intel)');
  assert(!targetArch.includes('universal'), 'mac target[dmg].arch does NOT include universal (Intel only)');

  // Windows target
  const win = cfg.win || {};
  const winTargets = Array.isArray(win.target)
    ? win.target.map(t => (typeof t === 'string' ? t : t.target))
    : [win.target];
  assert(winTargets.includes('nsis'), 'win target includes nsis');

  // Icon paths set
  const icons = cfg.mac?.icon || '';
  assert(icons.includes('icon.icns') || icons.includes('icons/'), 'mac icon path references icns file');
}

function testIcons() {
  section('App Icons');
  const iconDir = path.join(FRONTEND, 'build', 'icons');
  assert(fs.existsSync(iconDir), 'build/icons/ directory exists');

  const pngPath = path.join(iconDir, 'icon.png');
  assert(fs.existsSync(pngPath), 'icon.png exists');
  if (fs.existsSync(pngPath)) {
    try {
      const { width, height } = readPngDimensions(pngPath);
      assert(width === 512 && height === 512, `icon.png is 512x512 (got ${width}x${height})`);
    } catch (e) {
      assert(false, `icon.png is valid PNG (${e.message})`);
    }
  }

  const icnsPath = path.join(iconDir, 'icon.icns');
  assert(fs.existsSync(icnsPath), 'icon.icns exists');
  if (fs.existsSync(icnsPath)) {
    const buf = fs.readFileSync(icnsPath);
    // ICNS files start with magic 'icns' (0x69636e73)
    const magic = buf.slice(0, 4).toString('ascii');
    assert(magic === 'icns', `icon.icns has valid ICNS magic bytes (got "${magic}")`);
    assert(buf.length > 100, `icon.icns is not empty (${buf.length} bytes)`);
  }

  const icoPath = path.join(iconDir, 'icon.ico');
  assert(fs.existsSync(icoPath), 'icon.ico exists');
  if (fs.existsSync(icoPath)) {
    const buf = fs.readFileSync(icoPath);
    // ICO files start with 0x00 0x00 (reserved) 0x01 0x00 (type=1)
    const isIco = buf[0] === 0x00 && buf[1] === 0x00 && buf[2] === 0x01 && buf[3] === 0x00;
    assert(isIco, 'icon.ico has valid ICO magic bytes');
    assert(buf.length > 100, `icon.ico is not empty (${buf.length} bytes)`);
  }
}

function testPackageJson() {
  section('package.json build scripts');
  const pkgPath = path.join(FRONTEND, 'package.json');
  assert(fs.existsSync(pkgPath), 'package.json exists');

  const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

  assert(pkg.main === 'main.js', 'main points to main.js');
  assert(typeof pkg.author === 'string' && pkg.author.length > 0, 'author field is set');

  const s = pkg.scripts || {};
  assert(typeof s['build:mac'] === 'string', 'build:mac script exists');
  assert(typeof s['build:win'] === 'string', 'build:win script exists');
  assert(typeof s['build:dir'] === 'string', 'build:dir script exists');
  assert(typeof s['build:mac'] === 'string' && s['build:mac'].includes('electron-builder'), 'build:mac uses electron-builder');
  assert(typeof s['build:win'] === 'string' && s['build:win'].includes('electron-builder'), 'build:win uses electron-builder');
  assert(typeof s['build:dir'] === 'string' && (s['build:dir'].includes('electron-builder') || s['build:dir'].includes('--dir')), 'build:dir uses electron-builder --dir');
}

function testViteBuildOutput() {
  section('Vite build output (dist/)');
  const distPath = path.join(FRONTEND, 'dist');
  assert(fs.existsSync(distPath), 'dist/ directory exists');

  const indexPath = path.join(distPath, 'index.html');
  assert(fs.existsSync(indexPath), 'dist/index.html exists');
  if (fs.existsSync(indexPath)) {
    const content = fs.readFileSync(indexPath, 'utf8');
    assert(content.includes('<html'), 'dist/index.html contains <html>');
    assert(content.includes('<script'), 'dist/index.html contains <script> tag (JS bundled)');
  }

  const assetsPath = path.join(distPath, 'assets');
  assert(fs.existsSync(assetsPath), 'dist/assets/ directory exists');
  if (fs.existsSync(assetsPath)) {
    const assets = fs.readdirSync(assetsPath);
    assert(assets.some(f => f.endsWith('.js')), 'dist/assets/ contains .js bundle');
    assert(assets.some(f => f.endsWith('.css')), 'dist/assets/ contains .css bundle');
  }
}

function testGenerateIconsScript() {
  section('Icon generation script');
  const scriptPath = path.join(PROJECT_ROOT, 'scripts', 'generate_icons.py');
  assert(fs.existsSync(scriptPath), 'scripts/generate_icons.py exists');
  if (fs.existsSync(scriptPath)) {
    const content = fs.readFileSync(scriptPath, 'utf8');
    assert(content.includes('Pillow') || content.includes('PIL'), 'script uses Pillow/PIL');
    assert(content.includes('icon.png'), 'script generates icon.png');
    assert(content.includes('icon.icns') || content.includes('.icns'), 'script generates icon.icns');
    assert(content.includes('icon.ico') || content.includes('.ico'), 'script generates icon.ico');
  }
}

// ── Run all tests ────────────────────────────────────────────────────────────

console.log('Step 51 — Packaging Config Validation');
console.log('======================================');

testElectronBuilderYml();
testIcons();
testPackageJson();
testViteBuildOutput();
testGenerateIconsScript();

console.log(`\n======================================`);
console.log(`Results: ${passed} passed, ${failed} failed`);

if (failed > 0) {
  console.error('\nFailed tests:');
  errors.forEach(e => console.error(`  - ${e}`));
  process.exit(1);
} else {
  console.log('\nAll tests passed!');
  process.exit(0);
}
