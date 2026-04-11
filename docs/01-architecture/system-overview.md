# System Overview

> 정본. cmux orchestrator + watcher pack의 3계층 아키텍처, 데이터 흐름, 상태 머신을 정의한다.

## 3계층 구조

```
User / CEO
  |
  v
JARVIS (CEO Staff) ── 직속 참모, 설정 진화 + 멘토 코칭
  |
  v
Control Tower ── Boss(COO) + Watcher(감사실)
  |
  v
Departments ── Team Lead + Workers (tmux pane)
```

| 계층 | 구성 | 책임 |
|------|------|------|
| **CEO Staff** | JARVIS | 설정 진화, 멘토 코칭, 실패 분류, 사용자 직접 소통 |
| **Control Tower** | Boss + Watcher | Boss: 작업 분해/디스패치/수집/리뷰/커밋. Watcher: 4계층 감시/알림 |
| **Departments** | Lead + Workers | Lead: 워커 생성/AI 선택/검증. Workers: 독립 실행 |

## 데이터 흐름

```
Boss ──cmux send──> Worker tmux pane
Boss <──capture-pane── Worker (결과 수집)

Watcher ──4-layer scan──> All surfaces
Watcher ──status report──> Boss (IDLE/ERROR/STALL)

JARVIS ──policy propagate──> Boss, Watcher
JARVIS <──approve/reject──> User
JARVIS ──coaching hint──> /cmux context injection
```

## 상태 머신

`cmux-workflow-state-machine.py`가 강제한다.

```
IDLE → DISPATCH → COLLECT → VERIFY → COMMIT → IDLE
```

- DISPATCH: Boss가 `cmux send`로 worker에 작업 전달
- COLLECT: 모든 worker가 DONE 보고
- VERIFY: Boss가 코드 리뷰 (Sonnet agent)
- COMMIT: LECEIPTS 5-섹션 보고서 + git commit

## SSOT 맵

| 데이터 | SSOT | 보조/캐시 |
|--------|------|-----------|
| 로컬 AI preset | `orchestra-config.json`의 `presets` | `ai-profile.json` |
| runtime surface 상태 | `cmux tree --all` + `/tmp/cmux-surface-map.json` | `/tmp/cmux-surface-scan.json` |
| control tower role | `/tmp/cmux-roles.json` | tab name |
| 운영 메모리 | `~/.claude/memory/cmux/journal.jsonl` | `memories.json` |
| 멘토 신호 | `~/.claude/cmux-jarvis/mentor/signals.jsonl` | L0.md, L1.md |
| JARVIS 텔레메트리 | `~/.claude/cmux-jarvis/telemetry/events-*.jsonl` | ring buffer |

## 참조

- Orchestrator: [orchestrator-architecture.md](orchestrator-architecture.md)
- Watcher: [watcher-architecture.md](watcher-architecture.md)
- JARVIS: [../02-jarvis/constitution.md](../02-jarvis/constitution.md)
- Hooks: [hook-enforcement.md](hook-enforcement.md)
