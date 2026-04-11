# Troubleshooting

> 알려진 이슈와 복구 절차.

## Control Tower Guard False Positive

**증상**: 일반 `close-workspace` 명령이 control tower guard에 의해 차단됨.

**원인**: shlex 토큰 분석이 workspace ID를 control tower로 오인.

**해결**: `cmux-control-tower-guard.py`의 workspace ID 매칭 로직 확인. `/tmp/cmux-roles.json`에 올바른 role이 등록되어 있는지 확인.

## validate-config.sh NameError

**증상**: `NameError: name 'os' is not defined`

**원인**: embedded Python 블록에 `import os` 누락 (P0에서 수정 완료).

**해결**: 최신 버전으로 업데이트 (`bash install.sh`).

## Stale AI Detection

**증상**: `/cmux-config detect`에서 감지되는 AI와 Watcher의 `available_tools`가 다름.

**원인**: `ai-profile.json`의 `detected` 필드가 stale (P0에서 수정 완료).

**해결**: `watcher-scan.py`가 `shutil.which()`로 런타임 감지. 최신 버전으로 업데이트.
