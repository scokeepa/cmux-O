# Cross-Platform Compatibility

> macOS, Linux, WSL 호환 메커니즘.

## cmux_compat 데몬

OS별 명령어 차이를 추상화하는 Python 데몬.

- Unix socket: `/tmp/cmux-compat.sock`
- `/cmux-start` 시 자동 시작
- 데몬 불가 시 inline `python3` fallback

## 추상화 대상

| 명령 | macOS | Linux | 추상화 |
|------|-------|-------|--------|
| `grep -P` | 미지원 | 지원 | `python3 re` |
| `date -j` | 지원 | 미지원 | `python3 datetime` |
| `stat -f` | 지원 | `stat -c` | `python3 os.stat` |

## WSL 제약

- tmux 클립보드 통합 제한 (`win32yank` 필요)
- `/tmp` 경로가 Windows와 분리됨
- systemd 미지원 시 데몬 자동 시작 수동 설정 필요
