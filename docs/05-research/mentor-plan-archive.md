# AGI Mentor Integrated Plan — Archive Summary

> 원본: `99-archive/CMUX-AGI-MENTOR-INTEGRATED-PLAN.md` (1000줄+).
> P0~P6 구현 완료 후 핵심 결정만 요약. 세부는 원본 참조.

## 핵심 결정

### 흡수 원칙
- 외부 레포를 그대로 vendoring하지 않는다
- vibe-sunsang → Mentor Ontology로 흡수 (6축, Harness Level)
- mempalace → Palace Memory Substrate로 흡수 (L0~L3, JSONL/SQLite)
- badclaude → Nudge/Escalation Policy로 흡수 (session-scoped, OS 키 입력 금지)
- referense/1.jpeg, 2.jpeg → 제품 원칙으로만 사용 (외부 사실 주장 금지)

### 실행 계획 (전부 완료)
| Phase | 내용 | 상태 |
|-------|------|------|
| P0 | validate-config.sh + stale AI detection + config deprecation | 완료 |
| P1 | 아키텍처 문서 7건 | 완료 |
| P2+P3 | Palace Memory SSOT + signal engine + redactor | 완료 |
| P4+P4.1 | Context injection + Nudge L1 | 완료 |
| P5+P6 | Mentor Report + Failure Classifier | 완료 |

### Readiness Gate 결론
- L1 nudge: 즉시 가능
- L2 interrupt: cmux session ID 경로 확인 후 (보류)
- ChromaDB/MCP: Phase 3+ optional
- Raw drawer 저장: opt-in schema만 (코드 미구현)

## 원본 위치
`docs/99-archive/CMUX-AGI-MENTOR-INTEGRATED-PLAN.md`
