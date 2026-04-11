#!/usr/bin/env python3
"""tests/test_nudge.py — jarvis_nudge.py ChromaDB 단위 테스트."""

import json
import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cmux-jarvis", "scripts"))
import jarvis_nudge as nudge


def _mock_cmux_send(target, message):
    """테스트용: cmux binary 없이 성공 반환."""
    return True


def _setup(td):
    nudge.PALACE_PATH = os.path.join(td, "palace")
    nudge.COLLECTION_NAME = "test_signals"


def test_l1_send():
    """L1 재촉 → palace drawer 기록."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        with patch.object(nudge, "_cmux_send", _mock_cmux_send):
            rc = nudge.cmd_send("surface:7", "team_lead", "STALLED", "8분간 진행 없음")
        assert rc == 0

        col = nudge._get_collection()
        results = col.get(where={"wing": "cmux_nudge"})
        assert len(results["ids"]) == 1
    print("  test_l1_send: PASS")


def test_watcher_blocked():
    """issuer=watcher → 거부."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        rc = nudge.cmd_send("surface:7", "watcher", "STALLED", "test")
        assert rc == 1
    print("  test_watcher_blocked: PASS")


def test_cooldown_enforced():
    """5분 내 재전송 → rate_limited."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        with patch.object(nudge, "_cmux_send", _mock_cmux_send):
            rc1 = nudge.cmd_send("surface:7", "team_lead", "STALLED", "stuck")
            assert rc1 == 0
            rc2 = nudge.cmd_send("surface:7", "team_lead", "STALLED", "still stuck")
            assert rc2 == 2
    print("  test_cooldown_enforced: PASS")


def test_l2_blocked():
    """level=L2 → 거부."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        rc = nudge.cmd_send("surface:7", "boss", "STALLED", "test", level="L2")
        assert rc == 1
    print("  test_l2_blocked: PASS")


def test_invalid_issuer():
    """유효하지 않은 issuer → 거부."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        rc = nudge.cmd_send("surface:7", "worker", "STALLED", "test")
        assert rc == 1
    print("  test_invalid_issuer: PASS")


def test_different_targets_no_cooldown():
    """다른 target은 cooldown 독립."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        with patch.object(nudge, "_cmux_send", _mock_cmux_send):
            rc1 = nudge.cmd_send("surface:7", "team_lead", "STALLED", "stuck")
            rc2 = nudge.cmd_send("surface:8", "team_lead", "IDLE", "idle")
        assert rc1 == 0
        assert rc2 == 0
    print("  test_different_targets_no_cooldown: PASS")


def test_check_cooldown():
    """cooldown 상태 확인."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        in_cd, _ = nudge._check_cooldown("surface:99")
        assert not in_cd

        with patch.object(nudge, "_cmux_send", _mock_cmux_send):
            nudge.cmd_send("surface:99", "boss", "IDLE", "5분")
        in_cd2, _ = nudge._check_cooldown("surface:99")
        assert in_cd2
    print("  test_check_cooldown: PASS")


def test_nudge_excluded_from_mentor_context():
    """cmux_nudge wing 데이터가 mentor context 생성에 포함되지 않아야 함."""
    import jarvis_palace_memory as pm
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        pm.PALACE_PATH = nudge.PALACE_PATH
        pm.COLLECTION_NAME = nudge.COLLECTION_NAME

        # mentor signal + nudge audit 둘 다 저장
        col = nudge._get_collection()
        col.add(
            ids=["mentor-1", "nudge-1"],
            documents=["decomp 0.9 verify 0.8", "NUDGE L1 → surface:7: stuck"],
            metadatas=[
                {"wing": "cmux_mentor", "room": "decomp", "ts": "2026-04-01T00:00:00Z",
                 "fit_score": 0.8, "harness_level": 2.0, "confidence": 0.7,
                 "evidence_count": "5", "coaching_hint": "keep going",
                 "calibration_note": "ok", "antipatterns": "",
                 "decomp": 0.9, "verify": 0.8, "orch": 0.7, "fail": 0.6, "ctx": 0.5, "meta": 0.4},
                {"wing": "cmux_nudge", "room": "stalled", "ts": "2026-04-01T00:01:00Z",
                 "target_surface_id": "surface:7", "issuer_role": "team_lead",
                 "reason_code": "STALLED", "level": "L1", "outcome": "sent"},
            ],
        )

        # generate_l1은 wing=cmux_mentor만 포함해야 함
        l1 = pm.generate_l1()
        assert "NUDGE" not in l1
        assert "surface:7" not in l1
        assert "stalled" not in l1.lower() or "STALLED" not in l1
    print("  test_nudge_excluded_from_mentor_context: PASS")


def test_send_failure_sets_outcome_failed():
    """cmux send 실패 시 outcome='failed', return code=3."""
    def _mock_fail(target, message):
        return False

    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        with patch.object(nudge, "_cmux_send", _mock_fail):
            rc = nudge.cmd_send("surface:7", "team_lead", "STALLED", "stuck")
        assert rc == 3

        # audit에 outcome=failed 기록 확인
        col = nudge._get_collection()
        results = col.get(where={"wing": "cmux_nudge"}, include=["metadatas"])
        assert len(results["ids"]) == 1
        assert results["metadatas"][0]["outcome"] == "failed"
    print("  test_send_failure_sets_outcome_failed: PASS")


def test_cross_workspace_blocked():
    """team_lead가 다른 workspace의 target에 nudge → 거부 (code 4)."""
    roles = {
        "team_lead": {"surface": "surface:3", "workspace": "ws1"},
        "worker_ws2": {"surface": "surface:7", "workspace": "ws2"},
    }
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        with patch.object(nudge, "_load_runtime_json", return_value=roles):
            with patch.object(nudge, "_cmux_send", _mock_cmux_send):
                rc = nudge.cmd_send("surface:7", "team_lead", "STALLED", "stuck")
        assert rc == 4
    print("  test_cross_workspace_blocked: PASS")


def test_same_workspace_allowed():
    """team_lead가 같은 workspace의 target에 nudge → 허용."""
    roles = {
        "team_lead": {"surface": "surface:3", "workspace": "ws1"},
        "worker_ws1": {"surface": "surface:7", "workspace": "ws1"},
    }
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        with patch.object(nudge, "_load_runtime_json", return_value=roles):
            with patch.object(nudge, "_cmux_send", _mock_cmux_send):
                rc = nudge.cmd_send("surface:7", "team_lead", "STALLED", "stuck")
        assert rc == 0
    print("  test_same_workspace_allowed: PASS")


def test_no_roles_file_fallback():
    """roles.json 없으면 기존 ALLOWED_ISSUERS 검증만 적용."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td)
        with patch.object(nudge, "_load_runtime_json", return_value=None):
            with patch.object(nudge, "_cmux_send", _mock_cmux_send):
                rc = nudge.cmd_send("surface:7", "boss", "IDLE", "no progress")
        assert rc == 0
    print("  test_no_roles_file_fallback: PASS")


def main():
    test_l1_send()
    test_watcher_blocked()
    test_cooldown_enforced()
    test_l2_blocked()
    test_invalid_issuer()
    test_different_targets_no_cooldown()
    test_check_cooldown()
    print("\nAll nudge (ChromaDB) tests passed.")


if __name__ == "__main__":
    main()
