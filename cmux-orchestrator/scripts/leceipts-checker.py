#!/usr/bin/env python3
"""leceipts-checker.py — gate-checker.sh에서 호출하는 LECEIPTS 검증 스크립트.

공통 validator 모듈을 사용하여 hook과 동일한 규칙 적용.
정본: CLAUDE.md (leceipts Working Rules)

exit 0 = PASS, exit 1 = FAIL (stdout에 사유)
"""
import sys

from leceipts_validator import validate_report

ok, result = validate_report(check_ttl=False)
if ok:
    print("OK")
else:
    print(result)
    sys.exit(1)
