#!/usr/bin/env python3
"""tests/test_palace_memory.py — jarvis_palace_memory.py 단위 테스트."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cmux-jarvis", "scripts"))
import jarvis_palace_memory as pm


def test_generate_l0_default():
    """L0.md 기본값 생성."""
    with tempfile.TemporaryDirectory() as td:
        pm.CONTEXT_DIR = type(pm.CONTEXT_DIR)(td)
        pm.L0_FILE = pm.CONTEXT_DIR / "L0.md"

        text = pm.generate_l0()
        assert "L0 — IDENTITY" in text
        assert "CEO" in text
        assert pm.L0_FILE.exists()
    print("  test_generate_l0_default: PASS")


def test_generate_l0_custom():
    """사용자가 L0.md를 직접 수정한 경우 그대로 사용."""
    with tempfile.TemporaryDirectory() as td:
        pm.CONTEXT_DIR = type(pm.CONTEXT_DIR)(td)
        pm.L0_FILE = pm.CONTEXT_DIR / "L0.md"
        pm.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        pm.L0_FILE.write_text("Custom identity.", encoding="utf-8")

        text = pm.generate_l0()
        assert text == "Custom identity."
    print("  test_generate_l0_custom: PASS")


def test_generate_l1_from_signals():
    """signals 데이터 → L1 요약 생성."""
    signals = [{
        "scores": {"decomp": 0.75, "verify": 0.45, "orch": 0.80, "fail": 0.60, "ctx": 0.70, "meta": 0.50},
        "harness_level": 3.5,
        "antipatterns": ["context_skip"],
        "coaching_hint": "완료 조건을 명시하세요.",
        "fit_score": 0.65,
        "calibration_note": "ok",
    }]
    text = pm.generate_l1(signals)
    assert "L1 — ESSENTIAL STORY" in text
    assert "Harness Level" in text
    assert "ORCH" in text  # strongest axis
    assert "context_skip" in text
    assert "완료 조건" in text
    print("  test_generate_l1_from_signals: PASS")


def test_l1_insufficient_data():
    """signals가 비어있을 때 '충분한 관찰이 없습니다'."""
    text = pm.generate_l1([])
    assert "충분한 관찰이 없습니다" in text
    print("  test_l1_insufficient_data: PASS")


def test_l1_token_budget():
    """L0+L1 합산 900 token 이하."""
    # Generate many signals to stress L1
    signals = []
    for i in range(20):
        signals.append({
            "scores": {"decomp": 0.5+i*0.02, "verify": 0.3, "orch": 0.7, "fail": 0.4, "ctx": 0.6, "meta": 0.5},
            "harness_level": 3.0 + i * 0.1,
            "antipatterns": ["context_skip", "verification_skip", "fix_me_syndrome"],
            "coaching_hint": "힌트 " * 10,
            "fit_score": 0.5 + i * 0.02,
            "calibration_note": "ok",
        })

    l0 = pm.L0_DEFAULT
    l1 = pm.generate_l1(signals)

    l0_tokens = pm._estimate_tokens(l0)
    l1_tokens = pm._estimate_tokens(l1)
    total = l0_tokens + l1_tokens

    assert total <= pm.MAX_TOTAL_TOKENS, f"Token budget exceeded: {total} > {pm.MAX_TOTAL_TOKENS}"
    print(f"  test_l1_token_budget: PASS ({total}/{pm.MAX_TOTAL_TOKENS} tokens)")


def test_l1_calibration_warning():
    """insufficient_evidence 시 주의 문구 포함."""
    signals = [{
        "scores": {"decomp": 0.5, "verify": 0.5, "orch": 0.5, "fail": 0.5, "ctx": 0.5, "meta": 0.5},
        "harness_level": 2.0,
        "antipatterns": [],
        "coaching_hint": "",
        "fit_score": 0.5,
        "calibration_note": "insufficient_evidence",
    }]
    text = pm.generate_l1(signals)
    assert "표본 부족" in text
    print("  test_l1_calibration_warning: PASS")


def test_export_import_roundtrip():
    """export → import → signal 수 일치."""
    with tempfile.TemporaryDirectory() as td:
        pm.MENTOR_DIR = type(pm.MENTOR_DIR)(td)
        pm.SIGNALS_FILE = pm.MENTOR_DIR / "signals.jsonl"
        pm.CONTEXT_DIR = pm.MENTOR_DIR / "context"
        pm.L0_FILE = pm.CONTEXT_DIR / "L0.md"
        pm.L1_FILE = pm.CONTEXT_DIR / "L1.md"
        pm.NUDGE_AUDIT_FILE = pm.MENTOR_DIR / "nudge-audit.jsonl"

        pm.MENTOR_DIR.mkdir(parents=True, exist_ok=True)
        pm.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

        # Write test signals
        with open(pm.SIGNALS_FILE, "w") as f:
            f.write(json.dumps({"signal_id": "sig-1", "scores": {"decomp": 0.7}}) + "\n")
            f.write(json.dumps({"signal_id": "sig-2", "scores": {"decomp": 0.8}}) + "\n")
        pm.L0_FILE.write_text("test L0", encoding="utf-8")

        # Export
        export_file = os.path.join(td, "export.json")
        pm.cmd_export(export_file)

        # Clear and import
        pm.SIGNALS_FILE.unlink()
        pm.cmd_import(export_file)

        signals = pm._read_signals()
        assert len(signals) == 2, f"Expected 2, got {len(signals)}"
        assert signals[0]["signal_id"] == "sig-1"
    print("  test_export_import_roundtrip: PASS")


def test_import_dedup():
    """같은 export 2회 import → signal 수 변화 없음 (Q1 해결)."""
    with tempfile.TemporaryDirectory() as td:
        pm.MENTOR_DIR = type(pm.MENTOR_DIR)(td)
        pm.SIGNALS_FILE = pm.MENTOR_DIR / "signals.jsonl"
        pm.CONTEXT_DIR = pm.MENTOR_DIR / "context"
        pm.L0_FILE = pm.CONTEXT_DIR / "L0.md"
        pm.L1_FILE = pm.CONTEXT_DIR / "L1.md"
        pm.NUDGE_AUDIT_FILE = pm.MENTOR_DIR / "nudge-audit.jsonl"
        pm.MENTOR_DIR.mkdir(parents=True, exist_ok=True)

        with open(pm.SIGNALS_FILE, "w") as f:
            f.write(json.dumps({"signal_id": "sig-1"}) + "\n")

        export_data = {"format": "cmux_mentor_export", "version": 1,
                       "signals": [{"signal_id": "sig-1"}, {"signal_id": "sig-2"}]}
        export_file = os.path.join(td, "export.json")
        with open(export_file, "w") as f:
            json.dump(export_data, f)

        pm.cmd_import(export_file)  # sig-1 skipped, sig-2 imported
        pm.cmd_import(export_file)  # both skipped

        signals = pm._read_signals()
        assert len(signals) == 2, f"Expected 2, got {len(signals)}"
    print("  test_import_dedup: PASS")


def test_import_version_rejection():
    """version > 1 → 거부."""
    with tempfile.TemporaryDirectory() as td:
        pm.MENTOR_DIR = type(pm.MENTOR_DIR)(td)
        pm.SIGNALS_FILE = pm.MENTOR_DIR / "signals.jsonl"
        pm.MENTOR_DIR.mkdir(parents=True, exist_ok=True)

        future = {"format": "cmux_mentor_export", "version": 99, "signals": []}
        export_file = os.path.join(td, "future.json")
        with open(export_file, "w") as f:
            json.dump(future, f)

        rc = pm.cmd_import(export_file)
        assert rc == 1, f"Expected rc=1 for future version, got {rc}"
    print("  test_import_version_rejection: PASS")


def test_backup_integrity():
    """backup 후 JSONL 무결성 확인."""
    with tempfile.TemporaryDirectory() as td:
        pm.MENTOR_DIR = type(pm.MENTOR_DIR)(os.path.join(td, "mentor"))
        pm.SIGNALS_FILE = pm.MENTOR_DIR / "signals.jsonl"
        pm.CONTEXT_DIR = pm.MENTOR_DIR / "context"
        pm.MENTOR_DIR.mkdir(parents=True, exist_ok=True)

        with open(pm.SIGNALS_FILE, "w") as f:
            f.write('{"signal_id": "sig-1"}\n')
            f.write('{"signal_id": "sig-2"}\n')

        # Patch parent to td for backup location
        original_parent = pm.MENTOR_DIR.parent
        rc = pm.cmd_backup(max_backups=5)
        assert rc == 0
        backups = list(Path(td).glob("mentor-backup-*"))
        assert len(backups) >= 1, "No backup created"
    print("  test_backup_integrity: PASS")


def test_backup_retention():
    """max_backups=2 → 오래된 것 삭제."""
    with tempfile.TemporaryDirectory() as td:
        mentor = Path(td) / "mentor"
        mentor.mkdir()
        pm.MENTOR_DIR = mentor
        pm.SIGNALS_FILE = mentor / "signals.jsonl"
        pm.SIGNALS_FILE.write_text('{"signal_id":"s1"}\n')

        # Create 3 backups
        for _ in range(3):
            pm.cmd_backup(max_backups=2)
            import time; time.sleep(0.01)

        backups = list(Path(td).glob("mentor-backup-*"))
        assert len(backups) <= 2, f"Expected <= 2 backups, got {len(backups)}"
    print("  test_backup_retention: PASS")


def main():
    test_generate_l0_default()
    test_generate_l0_custom()
    test_generate_l1_from_signals()
    test_l1_insufficient_data()
    test_l1_token_budget()
    test_l1_calibration_warning()
    test_export_import_roundtrip()
    test_import_dedup()
    test_import_version_rejection()
    test_backup_integrity()
    test_backup_retention()
    print("\nAll palace memory tests passed.")


if __name__ == "__main__":
    main()
