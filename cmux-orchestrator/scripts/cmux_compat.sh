#!/usr/bin/env bash
# cmux_compat.sh — 크로스플랫폼 유틸리티 헬퍼
#
# 사용법: source cmux_compat.sh
# 이후 compat_json_get, compat_epoch 등 함수 사용.
# 데먼(cmux_compat.py) 실행 중이면 소켓 통신, 아니면 python3 인라인 폴백.

COMPAT_SOCK="/tmp/cmux-compat.sock"
# bash: BASH_SOURCE, zsh: funcfiletrace (0 is source file)
_COMPAT_SH_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
    _COMPAT_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [ -n "${funcfiletrace[1]:-}" ] 2>/dev/null; then
    _COMPAT_SH_DIR="$(cd "$(dirname "${funcfiletrace[1]%%:*}")" 2>/dev/null && pwd)"
fi
COMPAT_PY_CANDIDATES=(
    "$HOME/.claude/skills/cmux-orchestrator/scripts/cmux_compat.py"
)
[ -n "$_COMPAT_SH_DIR" ] && COMPAT_PY_CANDIDATES=("${_COMPAT_SH_DIR}/cmux_compat.py" "${COMPAT_PY_CANDIDATES[@]}")

_compat_find_py() {
    for p in "${COMPAT_PY_CANDIDATES[@]}"; do
        [ -f "$p" ] && echo "$p" && return 0
    done
    return 1
}

# ─── 데먼 관리 ───

compat_ensure_daemon() {
    [ -S "$COMPAT_SOCK" ] && return 0
    local py
    py=$(_compat_find_py) || return 1
    python3 "$py" start 2>/dev/null
    local i
    for i in 1 2 3 4 5 6; do
        [ -S "$COMPAT_SOCK" ] && return 0
        sleep 0.5
    done
    return 1
}

compat_stop_daemon() {
    local py
    py=$(_compat_find_py) || return 1
    python3 "$py" stop 2>/dev/null
}

# ─── 소켓 요청 (내부) ───

_compat_sock_request() {
    local req="$1"
    python3 -c "
import socket, sys, json
try:
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(3)
    s.connect('$COMPAT_SOCK')
    s.sendall(json.dumps($req).encode() + b'\n')
    resp = s.makefile().readline().strip()
    s.close()
    print(resp)
except Exception as e:
    print(json.dumps({'ok': False, 'error': str(e)}))
" 2>/dev/null
}

# ─── 인라인 폴백 (내부) ───

_compat_inline_request() {
    local req="$1"
    local py
    py=$(_compat_find_py) || { echo '{"ok":false,"error":"cmux_compat.py not found"}'; return 1; }
    echo "$req" | python3 "$py" --inline 2>/dev/null
}

# ─── 통합 요청 ───

_compat_request() {
    local req="$1"
    if [ -S "$COMPAT_SOCK" ]; then
        _compat_sock_request "$req"
    else
        _compat_inline_request "$req"
    fi
}

# JSON 응답에서 value 추출
_compat_extract_value() {
    python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    if d.get('ok'):
        v = d.get('value', '')
        print(v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False))
    else:
        print('', end='')
except:
    print('', end='')
" 2>/dev/null
}

# ─── 공개 함수: JSON ───

compat_json_get() {
    # compat_json_get FILE KEY
    local file="$1" key="$2"
    _compat_request "{\"cmd\":\"json-get\",\"args\":{\"file\":\"$file\",\"key\":\"$key\"}}" | _compat_extract_value
}

compat_json_set() {
    # compat_json_set FILE KEY VALUE
    local file="$1" key="$2" value="$3"
    _compat_request "{\"cmd\":\"json-set\",\"args\":{\"file\":\"$file\",\"key\":\"$key\",\"value\":$value}}" | _compat_extract_value
}

compat_json_query() {
    # compat_json_query FILE EXPR
    local file="$1" expr="$2"
    _compat_request "{\"cmd\":\"json-query\",\"args\":{\"file\":\"$file\",\"expr\":\"$expr\"}}" | _compat_extract_value
}

# ─── 공개 함수: 시간 ───

compat_epoch() {
    # compat_epoch [TIMESTAMP]  — 인자 없으면 현재 시간
    local ts="${1:-}"
    if [ -z "$ts" ]; then
        _compat_request '{"cmd":"epoch","args":{}}' | _compat_extract_value
    else
        _compat_request "{\"cmd\":\"epoch\",\"args\":{\"timestamp\":\"$ts\"}}" | _compat_extract_value
    fi
}

# ─── 공개 함수: 파일 ───

compat_stat_mtime() {
    # compat_stat_mtime FILE → epoch 초
    local file="$1"
    _compat_request "{\"cmd\":\"stat-mtime\",\"args\":{\"file\":\"$file\"}}" | _compat_extract_value
}

compat_stat_size() {
    # compat_stat_size FILE → bytes
    local file="$1"
    _compat_request "{\"cmd\":\"stat-size\",\"args\":{\"file\":\"$file\"}}" | _compat_extract_value
}

compat_readlink() {
    # compat_readlink FILE → 실제 경로
    local file="$1"
    _compat_request "{\"cmd\":\"readlink\",\"args\":{\"file\":\"$file\"}}" | _compat_extract_value
}

# ─── 공개 함수: 텍스트 ───

compat_grep_pcre() {
    # compat_grep_pcre PATTERN FILE → 매치 목록 (JSON array)
    local pattern="$1" file="$2"
    local escaped_pattern
    escaped_pattern=$(python3 -c "import json;print(json.dumps('$pattern')[1:-1])" 2>/dev/null)
    _compat_request "{\"cmd\":\"grep-pcre\",\"args\":{\"pattern\":\"$escaped_pattern\",\"file\":\"$file\"}}" | _compat_extract_value
}

compat_sed_inplace() {
    # compat_sed_inplace FILE PATTERN REPLACEMENT
    local file="$1" pattern="$2" replacement="$3"
    local ep er
    ep=$(python3 -c "import json;print(json.dumps('$pattern')[1:-1])" 2>/dev/null)
    er=$(python3 -c "import json;print(json.dumps('$replacement')[1:-1])" 2>/dev/null)
    _compat_request "{\"cmd\":\"sed-inplace\",\"args\":{\"file\":\"$file\",\"pattern\":\"$ep\",\"replacement\":\"$er\"}}" | _compat_extract_value
}

# ─── 공개 함수: 기타 ───

compat_base64_decode() {
    # compat_base64_decode STRING
    local data="$1"
    _compat_request "{\"cmd\":\"base64-decode\",\"args\":{\"data\":\"$data\"}}" | _compat_extract_value
}

compat_mktemp() {
    # compat_mktemp [PREFIX] [SUFFIX]
    local prefix="${1:-cmux-}" suffix="${2:-}"
    _compat_request "{\"cmd\":\"mktemp\",\"args\":{\"prefix\":\"$prefix\",\"suffix\":\"$suffix\"}}" | _compat_extract_value
}

compat_os_detect() {
    # compat_os_detect → JSON {os, arch, wsl, python}
    _compat_request '{"cmd":"os-detect","args":{}}' | _compat_extract_value
}

compat_version_check() {
    # compat_version_check COMMAND → JSON {version, raw}
    local cmd="$1"
    _compat_request "{\"cmd\":\"version-check\",\"args\":{\"command\":\"$cmd\"}}" | _compat_extract_value
}
