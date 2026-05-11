# VIA UI / API Integration — Manual E2E Test Checklist

> Run after `npm run dev` (frontend) + `uvicorn main:app` (backend, port 8000).
> Tick each item. Re-test items marked ⚠ after any layout change.

---

## 1. Input Panel

| # | Action | Expected | Pass |
|---|--------|----------|------|
| 1.1 | Click "Input" in sidebar | InputPanel renders | [ ] |
| 1.2 | Click "Upload Analysis Images" | File picker opens | [ ] |
| 1.3 | Select a valid image (JPG/PNG) | Thumbnail appears, filename shown | [ ] |
| 1.4 | Select a non-image file | Validation error shown | [ ] |
| 1.5 | Click delete icon on a thumbnail | Image removed from list | [ ] |
| 1.6 | Upload several images then click "Clear All" | All thumbnails removed | [ ] |
| 1.7 | Upload Test images (purpose = test) | Separate list rendered correctly | [ ] |
| 1.8 | Reload panel (navigate away, return) | Images still listed (Redux state persists) | [ ] |

---

## 2. Directive Panel

| # | Action | Expected | Pass |
|---|--------|----------|------|
| 2.1 | Click "Directive" in sidebar | 8 agent cards rendered | [ ] |
| 2.2 | Click "오케스트레이터" card header | Card expands, textarea visible | [ ] |
| 2.3 | Click expanded card header again | Card collapses, textarea hidden | [ ] |
| 2.4 | Expand card A then click card B | Card A collapses (accordion behavior) | [ ] |
| 2.5 | Type directive text in textarea then blur | Preview text appears on collapsed card | [ ] |
| 2.6 | Click "Save All" | API called; success indicator shown | [ ] |
| 2.7 | Click "Reset All" | All directives cleared; Redux store reset | [ ] |
| 2.8 | Simulate API error on save | Error state shown inside panel | [ ] |

---

## 3. Config Panel

| # | Action | Expected | Pass |
|---|--------|----------|------|
| 3.1 | Click "Config" in sidebar | ConfigPanel renders with mode toggle | [ ] |
| 3.2 | Toggle mode to "align" | Align-specific criteria fields appear | [ ] |
| 3.3 | Toggle back to "inspection" | Inspection-specific fields appear | [ ] |
| 3.4 | Enter invalid value (e.g., accuracy > 1.0) | Warning or validation shown | [ ] |
| 3.5 | Click "Save Config" with valid values | API called; success feedback shown | [ ] |
| 3.6 | Reload panel | Last saved config values pre-populated | [ ] |

---

## 4. Execution Panel

| # | Action | Expected | Pass |
|---|--------|----------|------|
| 4.1 | Click "Execution" in sidebar | Purpose textarea + Start button rendered | [ ] |
| 4.2 | Click Start with empty textarea | Button disabled; no API call | [ ] |
| 4.3 | Enter purpose text, click Start | API called; status badge shows "running" | [ ] |
| 4.4 | While running: wait 2 s | Current agent + iteration update via polling | [ ] |
| 4.5 | Click Cancel while running | cancelExecution called; status → "failed" | [ ] |
| 4.6 | Execution completes (status success) | success-message appears | [ ] |
| 4.7 | Simulate API error on start | start-error element shown | [ ] |

---

## 5. Result Panel

| # | Action | Expected | Pass |
|---|--------|----------|------|
| 5.1 | Click "Result" before any execution | Empty state rendered ("실행 결과가 여기에 표시됩니다") | [ ] |
| 5.2 | After successful execution, click "Result" | summary-text visible; tabs shown | [ ] |
| 5.3 | Default tab = Code | code-block with line numbers displayed | [ ] |
| 5.4 | Click Metrics tab | MetricsChart renders with bars | [ ] |
| 5.5 | Click Pipeline tab | PipelineViewer renders blocks with arrows | [ ] |
| 5.6 | Click Decision tab | decision-badge + reason + suggestions list | [ ] |
| 5.7 | Click Code tab again | code-block returns, no other sections visible | [ ] |
| 5.8 | Python keywords highlighted in code block | keywords appear in distinct color | [ ] |

---

## 6. Log Panel

| # | Action | Expected | Pass |
|---|--------|----------|------|
| 6.1 | Click "Log" in sidebar | LogPanel renders with toolbar | [ ] |
| 6.2 | Before any execution | empty-state shows ("No logs yet…") | [ ] |
| 6.3 | Agent filter dropdown default | "All Agents" selected | [ ] |
| 6.4 | Level filter dropdown | Shows DEBUG / INFO / WARNING / ERROR options | [ ] |
| 6.5 | Click Refresh button | getLogs API called; log list updates | [ ] |
| 6.6 | During running execution (switch to Log panel) | Log entries update every 2 s automatically | [ ] |
| 6.7 | Select specific agent in filter | Only logs from that agent displayed | [ ] |
| 6.8 | Select ERROR level filter | Only ERROR-level entries shown | [ ] |
| 6.9 | Click Clear button | All log entries removed; Redux entries = [] | [ ] |
| 6.10 | Same agent name → consistent badge color | Two entries from "orchestrator" have identical badge color | [ ] |
| 6.11 | Different agents → different badge colors | "orchestrator" and "spec" badges have distinct colors | [ ] |
| 6.12 | Timestamp format | Entries show HH:MM:SS.mmm format | [ ] |
| 6.13 | Many logs (50+) | Scroll container active; auto-scrolls to bottom on new entry | [ ] |
| 6.14 | log-count badge | Reflects current visible entry count | [ ] |

---

## 7. Cross-Panel

| # | Action | Expected | Pass |
|---|--------|----------|------|
| 7.1 | Navigate through all 6 panels | Each panel renders without errors | [ ] |
| 7.2 | Start execution, switch to Log panel | Execution still running; logs auto-updating | [ ] |
| 7.3 | Switch back to Execution panel | Status reflects current running state | [ ] |
| 7.4 | Complete an execution, check Result | Result panel shows data from completed run | [ ] |
| 7.5 | Redux state persists across panel switches | Config, directives, images not lost on navigation | [ ] |

---

## 8. Design Consistency

| # | Item | Expected | Pass |
|---|------|----------|------|
| 8.1 | Background color (all panels) | Pure black/near-black (#0a0a0a / #111111) — no blue/purple/green | [ ] |
| 8.2 | Cards / sections | Glass morphism: bg-white/5 backdrop-blur border-white/10 | [ ] |
| 8.3 | Button hover states | Visible feedback, 150 ms transition | [ ] |
| 8.4 | Empty states (all panels) | Icon + descriptive message; consistent style | [ ] |
| 8.5 | Loading spinners | RefreshCw animate-spin; consistent size | [ ] |
| 8.6 | Error states | accent_error (#f87171) color; informative message | [ ] |
| 8.7 | Icons | All from lucide-react; consistent stroke width | [ ] |
| 8.8 | Typography | Inter/system font; correct hierarchy (xs tracking-wider labels) | [ ] |
| 8.9 | Sidebar active indicator | ChevronRight + bg_secondary highlight | [ ] |
| 8.10 | Responsive layout | No overflow at 1280 × 800 and 1920 × 1080 | [ ] |

---

## 9. Overall UI Quality

| # | Criterion | Rating (1-5) | Notes |
|---|-----------|-------------|-------|
| 9.1 | Visual hierarchy clarity | | |
| 9.2 | Information density (not too sparse / cluttered) | | |
| 9.3 | Interaction feedback (hover, active, disabled states) | | |
| 9.4 | Color consistency (dark theme adherence) | | |
| 9.5 | Empty / error / loading state quality | | |
| 9.6 | Agent badge color readability on dark background | | |
| 9.7 | Log panel readability (monospace, spacing, contrast) | | |
| 9.8 | Overall "production-ready" feel | | |

---

_Last updated: 2026-05-05 — Step 40_
