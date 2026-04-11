#!/usr/bin/env python3
"""leceipts_validator.py — LECEIPTS 보고서 검증 공통 모듈.

hook(cmux-leceipts-gate.py)과 checker(leceipts-checker.py)가 동일 규칙 사용.
정본: CLAUDE.md (leceipts Working Rules)
"""
import json
import os
import re
import shlex
import time

REPORT_FILE = "/tmp/cmux-leceipts-report.json"
MAX_AGE = 300  # 5분
# 정본: CLAUDE.md (leceipts Working Rules §코드 변경 시 5-섹션 응답 형식)
REQUIRED_KEYS = [
    "root_cause",
    "change",
    "recurrence_prevention",
    "verification",
    "remaining_risk",
]
PLACEHOLDER_PATTERN = re.compile(
    r"^(\.\.\.|TBD|TODO|미정|placeholder)$", re.IGNORECASE
)
# git global options that take a value argument (next token)
_GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
_GIT_LONG_VALUE_OPTIONS = {"--git-dir", "--work-tree", "--namespace"}


def is_git_commit(command):
    """shlex 토큰 분석으로 git commit 서브커맨드 감지.

    git -C <dir>, --work-tree <dir> 등 값 인자를 받는 global option도
    올바르게 건너뛴다.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.endswith("git"):
            j = i + 1
            while j < len(tokens):
                t = tokens[j]
                if t in ("&&", "||", ";", "|"):
                    break
                # --option=value 형태 (값이 붙어있음)
                if any(t.startswith(f"{opt}=") for opt in _GIT_LONG_VALUE_OPTIONS):
                    j += 1
                    continue
                # 값 인자를 받는 option → 다음 토큰도 skip
                if t in _GIT_VALUE_OPTIONS:
                    j += 2
                    continue
                if t.startswith("-"):
                    j += 1
                    continue
                if "=" in t:
                    j += 1
                    continue
                if t == "commit":
                    return True
                break
        i += 1
    return False


def validate_report(check_ttl=True, check_diff_hash=None):
    """보고서 검증. 성공 시 (True, report_dict), 실패 시 (False, reason_string)."""
    if not os.path.exists(REPORT_FILE):
        return False, "FILE_NOT_FOUND"

    if check_ttl:
        try:
            age = time.time() - os.path.getmtime(REPORT_FILE)
            if age > MAX_AGE:
                return False, f"TTL_EXPIRED:{int(age)}s"
        except OSError:
            pass

    try:
        with open(REPORT_FILE) as f:
            report = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return False, f"JSON_ERROR:{e}"

    missing = [k for k in REQUIRED_KEYS if k not in report]
    if missing:
        return False, f"MISSING:{','.join(missing)}"

    # verification 구조 검증
    verification = report.get("verification")
    if isinstance(verification, list):
        # 구조화 형식: [{cmd, exit_code, output_excerpt}]
        has_success = False
        for entry in verification:
            if not isinstance(entry, dict):
                return False, "VERIFICATION_ENTRY_NOT_DICT"
            if "cmd" not in entry or "exit_code" not in entry:
                return False, "VERIFICATION_MISSING_CMD_OR_EXIT_CODE"
            if int(entry["exit_code"]) == 0:
                has_success = True
            else:
                if not entry.get("failure_reason"):
                    return False, (
                        f"VERIFICATION_FAILED:cmd={entry['cmd']},"
                        f"exit_code={entry['exit_code']}"
                    )
        if not has_success:
            return False, "NO_SUCCESSFUL_VERIFICATION"
    elif isinstance(verification, str):
        v = verification.strip()
        # placeholder 체크를 길이 체크보다 먼저 (reason 정확성)
        if PLACEHOLDER_PATTERN.match(v):
            return False, f"PLACEHOLDER:{v}"
        if not v or len(v) < 10:
            return False, "EMPTY_VERIFICATION"
    else:
        return False, "VERIFICATION_INVALID_TYPE"

    # diff hash 바인딩 (필수)
    if check_diff_hash is not None:
        report_hash = report.get("staged_diff_hash", "")
        if not report_hash:
            return False, "DIFF_HASH_MISSING"
        if report_hash != check_diff_hash:
            return False, (
                f"DIFF_HASH_MISMATCH:report={report_hash},current={check_diff_hash}"
            )

    return True, report
