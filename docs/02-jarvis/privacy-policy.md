# Mentor Privacy Policy

> 정본. Mentor Lane의 데이터 수집, 저장, 사용, 삭제 정책을 정의한다.

## 기본 원칙

- **raw 저장 OFF가 기본**. derived signal만 저장한다
- raw conversation drawer는 사용자가 명시적으로 opt-in한 경우에만 저장한다
- 사용자의 성격/심리/능력을 단정하는 데이터를 생성하거나 저장하지 않는다
- 모든 저장 데이터는 로컬 전용이다. 네트워크 전송하지 않는다

## 수집 범위

### 기본 수집 (opt-out 가능)

orchestration 이벤트에서 파생한 신호만 수집한다:

- `user_instruction_submitted` — 지시 이벤트 (내용이 아닌 메타데이터)
- `boss_plan_created` — 계획 생성 이벤트
- `department_created` — 부서 생성 이벤트
- `lead_done_reported` — 팀장 완료 보고
- `review_failed`, `verification_failed` — 검증 실패 이벤트
- `scope_changed`, `user_override` — 범위 변경 이벤트
- `nudge_requested`, `nudge_applied`, `nudge_ignored` — 재촉 이벤트

### opt-in 수집

사용자가 `mentor.raw_capture_enabled: true`를 설정한 경우에만:

- raw conversation drawer (원문 대화 발췌)
- 지시 텍스트 verbatim 저장

## 저장소 분리

| 저장소 | 경로 | 용도 | 변경 |
|--------|------|------|------|
| 운영 메모리 | `~/.claude/memory/cmux/journal.jsonl`, `memories.json` | orchestration event memory | 기존 유지, 변경 없음 |
| 멘토 신호 | `~/.cmux-jarvis-palace/` (ChromaDB, wing=cmux_mentor) | derived signal (6축 score, 안티패턴, confidence) | ChromaDB palace |
| 멘토 L0/L1 | L0: `~/.cmux-jarvis-palace/identity.txt`, L1: ChromaDB 실시간 생성 | 세션 시작 시 context injection용 | ChromaDB palace |
| 재촉 감사 | `~/.cmux-jarvis-palace/` (ChromaDB, wing=cmux_nudge) | nudge 전송 기록 | ChromaDB palace |
| 텔레메트리 | `~/.claude/cmux-jarvis/telemetry/events-YYYY-MM-DD.jsonl` | JARVIS 이벤트 | 기존 유지 |

운영 메모리와 멘토 신호는 별도 저장소에 분리한다. 하나의 `memories.json`에 합치지 않는다.

## Retention

| 데이터 | 보존 기간 | 만료 처리 |
|--------|-----------|-----------|
| ChromaDB cmux_mentor drawers | 90일 | `cmd_prune` (keep_days 기반 삭제) |
| L0 (identity.txt) | 사용자 편집 가능 | 영구 보존 |
| L1 | 세션 시작 시 ChromaDB에서 실시간 생성 | 영구 보존 불필요 |
| telemetry events | 기존 정책 유지 | ring buffer + daily JSONL |

## Prompt Injection 제한

- L0 + L1 합산 **600~900 token** 이내
- coaching hint **최대 1개/round**
- raw memory는 prompt에 **직접 주입 금지**
- L2/L3 deep search는 사용자 요청 또는 Boss/JARVIS의 evidence 부족 선언 시에만 실행

## 사용자 권리

### opt-out

`~/.claude/cmux-jarvis/config.json`에서 mentor 전체를 비활성화할 수 있다:

```json
{
  "mentor": {
    "enabled": false
  }
}
```

비활성화하면 signal 수집(`cmd_emit`), context 생성(`cmd_generate_context`), weekly report(`cmd_generate`)가 모두 중단된다.

### delete

사용자는 다음을 삭제할 수 있다:

- palace 전체: `~/.cmux-jarvis-palace/` 디렉터리 삭제 (삭제 전 export 권장)
- 특정 기간: `python3 jarvis_mentor_signal.py prune --keep-days N`
- 특정 wing: ChromaDB API로 wing 필터 삭제

### export

사용자는 데이터를 내보낼 수 있다:

- `python3 jarvis_palace_memory.py export --output backup.json` (JSON 형태)
- weekly report: Markdown 형태

## 민감 정보 필터링

signal과 raw drawer 저장 시 다음 패턴을 자동 redaction한다:

| 패턴 | 처리 |
|------|------|
| API key (`sk-`, `key-`, `token-` 등) | `[REDACTED_API_KEY]` |
| password (`password=`, `passwd:` 등) | `[REDACTED_PASSWORD]` |
| 인증 토큰 (`Bearer `, `Authorization:` 등) | `[REDACTED_TOKEN]` |

파일 경로는 저장을 허용한다. 작업 컨텍스트에 필수적이기 때문이다.

## raw drawer 정책 (opt-in 전용)

raw drawer 저장은 다음 조건이 모두 충족될 때만 활성화한다:

1. `mentor.raw_capture_enabled: true` 설정
2. retention period 설정 (기본 30일)
3. redaction 규칙 활성화

raw drawer 검색 결과는 **memory evidence**로만 취급한다. system fact로 승격하려면 별도 검증을 거쳐야 한다.

## SRP

Mentor Privacy Policy는 **동의, 보존, redaction, export/delete 정책만** 담당한다.

담당하지 않는 것:
- signal 분석 → Mentor Ontology, Signal Engine
- 저장 구현 → Palace Memory Adapter
- 검색 구현 → Palace Memory Adapter
- context injection 구현 → cmux-main-context.sh

## 참조

- Mentor Lane: [mentor-lane.md](mentor-lane.md)
- 운영 메모리: `cmux-orchestrator/scripts/agent-memory.sh`
- 텔레메트리: `cmux-jarvis/scripts/jarvis_telemetry.py`
