# Watcher Architecture

> 정본. 4계층 모니터링 엔진의 구조, 판정 로직, 제약을 정의한다.

## 역할

Watcher는 **감시와 알림만** 담당하는 전용 AI다. Boss와 peer 관계이며 상하 관계가 아니다.

## 4계층 판정 엔진

| 계층 | 방법 | 감지 대상 | 신뢰도 |
|------|------|-----------|--------|
| **L1 Eagle** | 텍스트 패턴 매칭 | IDLE/WORKING/ERROR/DONE | 중 |
| **L2 OCR** | Apple Vision 스크린 캡처 | 멈춤, 에러 다이얼로그 | 높 |
| **L2.5 VisionDiff** | 전후 스크린 비교 | 화면 고정 (stall) | 높 |
| **L3 Pipe-pane** | tmux raw output | Rate limit, context overflow | 최고 |

### 판정 규칙

1. WORKING/WAITING이 하나라도 있으면 → 해당 상태 (DONE 아님)
2. L3 pipe-pane DONE → DONE (최고 신뢰)
3. L1 DONE + L2 일치 → DONE
4. L1 IDLE + L2.5 화면 고정 → STALLED
5. DONE 판정 시 **30초 재검증 필수**

## 스캔 주기

- 기본 폴링: 20초 간격
- IDLE debounce: DONE 후 30초 유예 + 120초 min 재촉 간격
- 역할 필터링: Boss/Watcher/JARVIS 제외, worker만 감시

## 금지 사항 (GATE W-9)

Watcher는 다음을 하지 않는다:
- 작업 배정 / 코드 수정
- Surface 생성 / 해제
- Department 관리
- Worker 직접 복구 지시
- Nudge/Escalation 실행 (evidence producer만)

## 참조

- 세부 프로토콜: `cmux-watcher/SKILL.md`
- Vision Diff: `cmux-watcher/references/vision-diff-protocol.md`
- 통합 스캐너: `cmux-watcher/scripts/watcher-scan.py`
