# Quick Start Guide

> 설치, 시작, 운영, 종료 절차.

## 설치

```bash
bash install.sh
```

자동 수행 항목:
1. OS 감지 (macOS / Linux / WSL)
2. cmux, python3 버전 검증
3. 기존 settings.json + skills 백업
4. 9개 skill → `~/.claude/skills/`
5. 31개 hook symlink + settings.json 등록
6. AI CLI 자동 감지

## 시작

```bash
/cmux-start
```

3초 내 Control Tower 구성: Boss + Watcher + JARVIS

## 9개 명령어

| 명령 | 기능 |
|------|------|
| `/cmux-start` | Control tower 시작 + 기존 세션 감지 |
| `/cmux-stop` | 선택적 종료 (부서 / control tower / 전체) |
| `/cmux-orchestrator` | Boss: 분해 + 디스패치 + 수집 + 커밋 |
| `/cmux-watcher` | 4계층 모니터링 시작 |
| `/cmux-config` | AI 프로파일 관리 (detect / add / remove) |
| `/cmux-help` | 명령어 도움말 |
| `/cmux-pause` | 긴급 정지 + 재개 |
| `/cmux-uninstall` | 완전 제거 + 백업 롤백 |
| `cmux-jarvis` | 자기 진화 엔진 (자동 호출) |

## 종료

```bash
/cmux-stop
```
