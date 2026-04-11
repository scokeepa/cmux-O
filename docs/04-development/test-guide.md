# Test Guide

> 58 tests 구조, 실행 방법, 패턴.

## 실행

```bash
python3 -m pytest tests/ -v
```

## 테스트 구조

| 파일 | 테스트 수 | 대상 |
|------|-----------|------|
| `test_cmux_utils.py` | 9 | 핵심 유틸리티 (atomic write, locked update, queue) |
| `test_hooks.py` | 5 | Hook 강제 (fail-closed, fail-open, silent, approve) |
| `test_mentor_signal.py` | 5 | 6축 signal (emit, insufficient, fit score, antipattern, prune) |
| `test_palace_memory.py` | 6 | L0/L1 context (default, custom, signals, empty, budget, calibration) |
| `test_redaction.py` | 8 | 민감 정보 redaction (5 patterns + path + mixed + false positive) |
| `test_context_injection.py` | 5 | Mentor context inject (present, absent, spam, budget, empty hint) |
| `test_nudge.py` | 7 | L1 nudge (send, watcher block, cooldown, L2 block, invalid, targets, check) |
| `test_mentor_report.py` | 6 | Report (generate, insufficient, timeline, disclaimer, trend, gate) |
| `test_failure_classifier.py` | 7 | Failure classify (system, user, mixed, none, iron law, empty, evidence) |

## 패턴

- `tempfile.TemporaryDirectory()`로 격리된 테스트 환경
- 모듈 전역 경로를 임시 디렉터리로 교체 후 복원
- `assert` + `print("  test_name: PASS")` 패턴
- `main()` 함수에서 순차 실행 (pytest 호환)
