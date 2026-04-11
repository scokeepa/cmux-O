#!/usr/bin/env python3
"""mentor_redactor.py — signal/drawer 저장 전 민감 정보 자동 redaction.

SSOT: docs/02-jarvis/privacy-policy.md

Usage:
    python3 mentor_redactor.py --text "password=secret123 and sk-abc..."
    echo "Bearer eyJ..." | python3 mentor_redactor.py --stdin
"""

import argparse
import re
import sys

REDACTION_PATTERNS = [
    (re.compile(r'(?:sk|pk|rk|ak)-[A-Za-z0-9_-]{20,}'), '[REDACTED_API_KEY]'),
    (re.compile(r'(?:password|passwd|pwd)\s*[=:]\s*\S+', re.IGNORECASE), '[REDACTED_PASSWORD]'),
    (re.compile(r'Bearer\s+[A-Za-z0-9._-]+'), '[REDACTED_TOKEN]'),
    (re.compile(r'Authorization:\s*\S+', re.IGNORECASE), '[REDACTED_TOKEN]'),
    (re.compile(r'(?:token|secret|api_key)\s*[=:]\s*\S+', re.IGNORECASE), '[REDACTED_SECRET]'),
]


# ── Input sanitization (mempalace/config.py:22-57 동일 패턴) ──────────

MAX_NAME_LENGTH = 128
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_ .'-]{0,126}[a-zA-Z0-9]?$")


def sanitize_name(value, field_name="name"):
    """Validate wing/room/entity name. Blocks path traversal, null bytes, long strings."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    value = value.strip()
    if len(value) > MAX_NAME_LENGTH:
        raise ValueError(f"{field_name} exceeds maximum length of {MAX_NAME_LENGTH} characters")
    if ".." in value or "/" in value or "\\" in value:
        raise ValueError(f"{field_name} contains invalid path characters")
    if "\x00" in value:
        raise ValueError(f"{field_name} contains null bytes")
    if not _SAFE_NAME_RE.match(value):
        raise ValueError(f"{field_name} contains invalid characters")
    return value


def sanitize_content(value, max_length=100_000):
    """Validate drawer/signal content length."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("content must be a non-empty string")
    if len(value) > max_length:
        raise ValueError(f"content exceeds maximum length of {max_length} characters")
    if "\x00" in value:
        raise ValueError("content contains null bytes")
    return value


def redact(text):
    """Apply all redaction patterns to text. File paths are preserved."""
    for pattern, replacement in REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def main():
    parser = argparse.ArgumentParser(description="Mentor Redactor")
    parser.add_argument("--text", help="Text to redact")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    args = parser.parse_args()

    if args.text:
        print(redact(args.text))
    elif args.stdin:
        print(redact(sys.stdin.read()))
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
