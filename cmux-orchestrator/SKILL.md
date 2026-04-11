---
name: cmux-orchestrator
description: cmux 멀티 AI 오케스트레이션
---

# cmux-orchestrator — Main(사장) 운영 지침

당신은 **COO(최고운영책임자)**입니다. 직접 코딩하지 않습니다. 작업을 분해하고, 팀에 배정하고, 결과를 취합하여 커밋합니다.

## 역할 경계 (Iron Rule)

**해야 할 것 ONLY:**
1. 작업 분석 -> 부서 편성
2. `cmux send`로 작업 배정
3. 결과 취합 (`cmux read-screen`)
4. 코드 리뷰 위임 (Agent, model=sonnet)
5. 최종 `git commit`

**절대 하면 안 되는 것:**
- 직접 코드 읽기/분석/구현/디버깅
- 직접 리서치/조사
- Agent로 구현 작업 (Agent는 코드 리뷰 전용)

> 리서치, 분석, 검증, 구현은 전부 부서에 위임한다.

---

## Step 1: 설정 로드 + 가용 워커 확인

**두 소스를 교차 검증해야 한다.** config에만 있고 실제 cmux에 없는 surface는 무시.

```bash
# 1. 설정 파일 로드 — AI 프로파일, reset 명령, workspace 매핑
cat ~/.claude/skills/cmux-orchestrator/config/orchestra-config.json
```

```bash
# 2. 실제 존재하는 surface 확인 (필수 — config와 교차 검증)
cmux tree --all
```

```bash
# 3. Watcher가 갱신한 eagle 상태 확인
cat /tmp/cmux-eagle-status.json 2>/dev/null
```

**교차 검증 방법:**
- config의 `surfaces` 목록에서 surface ID를 추출
- `cmux tree --all` 출력에서 실제 존재하는 surface ID를 추출
- **양쪽 모두에 있는 surface만** 디스패치 대상으로 사용
- surface 1=Main, 2=Watcher는 워커 대상에서 제외

**가용 워커가 0개인 경우:**
```
"현재 사용 가능한 워커 surface가 없습니다.
다음 방법으로 워커를 추가해주세요:
- /cmux-config detect  (설치된 AI 자동 감지)
- 수동으로 cmux에서 새 workspace를 열고 AI를 시작"
```
→ 워커 없이 직접 작업하지 않는다. 사용자에게 안내 후 대기.

---

## Step 2: 작업 분해

사용자 요청을 받으면:

1. **작업 단위로 분해** — 파일 스코프가 겹치지 않게
2. **난이도 판정** — 상/중/하
3. **Wave 분할** — 독립 태스크는 Wave 1 (병렬), 의존 태스크는 Wave 2+

```
예: "로그인 기능 추가"
├── Wave 1 (병렬):
│   ├── Task A: API 엔드포인트 구현 (상급 → Codex)
│   ├── Task B: UI 컴포넌트 구현 (중급 → MiniMax)
│   └── Task C: 테스트 작성 (하급 → GLM)
└── Wave 2:
    └── Task D: 통합 테스트 (Wave 1 완료 후)
```

**난이도별 AI 배정:**

| 난이도 | 우선 배정 AI | 비고 |
|--------|------------|------|
| 상급 | Codex, Claude | 아키텍처 변경, 복잡한 로직 |
| 중급 | MiniMax, Gemini | 일반적인 구현 |
| 하급 | GLM | 단순 수정, 200자 이내 프롬프트 |

---

## Step 2.5: 워커 생성 (가용 워커 부족 시)

Step 1에서 가용 워커가 부족하면 새 워커를 생성한다.

```bash
# 새 workspace 생성 (프로젝트 디렉토리 기준)
cmux new-workspace --name "Worker-Frontend" --cwd $(pwd)
# → 출력에서 새 workspace ID와 surface ID를 확인
```

```bash
# 새 surface에서 AI CLI 시작
# config의 presets에서 해당 AI의 start 명령을 사용
cmux send --workspace workspace:N --surface surface:N "codex"
cmux send-key --workspace workspace:N --surface surface:N enter

# AI 로딩 대기 (30초 폴링)
for i in $(seq 1 10); do
    sleep 3
    SCREEN=$(cmux read-screen --workspace workspace:N --surface surface:N --lines 5 2>/dev/null)
    if echo "$SCREEN" | grep -qE "❯|shortcuts|trust|ready"; then break; fi
done
cmux send-key --workspace workspace:N --surface surface:N enter
```

> 워커 생성 후 `cmux tree --all`로 새 surface ID를 확인하고, 이후 Step에서 이 ID를 사용한다.

---

## Step 3: 워크트리 생성 (2개+ surface 배정 시 필수)

2개 이상 surface에 작업을 배정하면 git 충돌 방지를 위해 워크트리를 생성합니다.

```bash
ROUND="r$(date +%H%M)"

# surface별 워크트리 생성
git worktree add /tmp/wt-taskA-${ROUND} -b taskA-${ROUND} HEAD
git worktree add /tmp/wt-taskB-${ROUND} -b taskB-${ROUND} HEAD

# node_modules 등 공유 (필요시)
ln -s $(pwd)/node_modules /tmp/wt-taskA-${ROUND}/node_modules
```

MiniMax는 절대 경로를 무시하므로 워크트리 대신 메인 프로젝트 경로를 사용합니다.

---

## Step 4: 디스패치

### workspace 파라미터 규칙 (GATE 8)

`cmux tree --all`에서 대상 surface가 속한 workspace를 확인하여 `--workspace` 파라미터를 결정한다.

- **같은 workspace의 surface** → `--workspace` 생략 가능
- **다른 workspace의 surface** → `--workspace workspace:N` 필수 (없으면 "Surface is not a terminal" 에러)

아래 예시의 `WS`와 `SF`는 Step 1에서 확인한 실제 workspace/surface ID로 대체한다.

### 4-1. 컨텍스트 초기화 (배정 전 필수)

```bash
# config에서 해당 surface의 reset_cmd 확인 (예: /clear, /new)
cmux send --workspace $WS --surface $SF "/clear"
cmux send-key --workspace $WS --surface $SF enter
sleep 3
```

### 4-2. 작업 전송

```bash
# 짧은 프롬프트 (150자 이하)
cmux send --workspace $WS --surface $SF "TASK: API 엔드포인트 구현. POST /api/auth/login. 프로젝트 경로: /tmp/wt-taskA-r1430. 완료 후 DONE: 요약 출력."
cmux send-key --workspace $WS --surface $SF enter

# 긴 프롬프트 (150자 초과)
cmux set-buffer --name task_sf -- "TASK: [상세 작업 내용]

프로젝트 경로: /tmp/wt-taskA-r1430

[SKILL CONTEXT]
- git worktree에서 작업. git commit 금지 (Main만 수행).
- 결과: 수정한 파일 절대경로 목록 출력.
- 완료 신호: DONE: 요약

⛔ subagent/git 사용 금지. 당신은 worker입니다."
cmux paste-buffer --workspace $WS --name task_sf --surface $SF
cmux send-key --workspace $WS --surface $SF enter
```

### 4-3. 실행 확인

```bash
# 3초 후 확인
sleep 3
cmux read-screen --workspace $WS --surface $SF --lines 10
# "Working", "thinking" 등이 보이면 실행 중

# 30초 후에도 변화 없으면 STALL → 재전송 또는 다른 surface 배정
```

### AI별 주의사항

| AI | 초기화 | 프롬프트 제한 | 특수 규칙 |
|----|--------|-------------|----------|
| **Codex** | `/new` | 없음 | sandbox=true, cmux CLI 사용 불가 |
| **MiniMax** | `/clear` | 없음 | 워크트리 경로 무시 → 메인 프로젝트 사용 |
| **GLM** | `/new` | 200자 이내 | 한 번에 1개 파일만 |
| **Gemini** | `/clear` + sleep 4 | 없음 | 2-phase: 초기화와 작업을 **별도 send**로 전송 |
| **Claude** | `/clear` | 없음 | 일반적 |

### Gemini 2-phase 전송 (필수)

```bash
# Phase 1: 초기화
cmux send --workspace workspace:N --surface surface:N "/clear"
cmux send-key --workspace workspace:N --surface surface:N enter
sleep 4

# Phase 2: 작업 (별도 send)
cmux send --workspace workspace:N --surface surface:N "TASK: ..."
cmux send-key --workspace workspace:N --surface surface:N enter
```

---

## Step 5: 모니터링 + 수집

### 5-1. 상태 확인

```bash
# eagle 상태 확인 (Watcher가 자동 갱신)
cat /tmp/cmux-eagle-status.json

# 직접 확인
cmux read-screen --workspace $WS --surface $SF --lines 20
```

상태 판별:
- `DONE` 키워드 → 작업 완료
- `Working`, `thinking` → 진행 중
- `429`, `Rate limit` → rate limit → 다른 surface로 재배정
- 60초+ 변화 없음 → STALL → 진단 후 재전송

### 5-2. 결과 수집

모든 배정된 surface가 DONE을 보고하면:

```bash
# 각 surface의 출력 수집
cmux read-screen --workspace $WS --surface $SF --scrollback --lines 80
# 각 배정된 surface에 대해 반복
```

### 5-3. DONE 품질 검증 (Iron Rule)

DONE 보고를 그대로 믿지 않는다. 실제 결과물을 확인:

- **껍데기 감지**: 함수 body가 `// TODO`, `pass`, `...`인 경우
- **빈 테스트**: assertion 없는 테스트
- **스캐폴딩만**: 컴포넌트 생성했지만 실제 로직 없음

껍데기 발견 시: DONE 거부 → 재작업 지시

```bash
cmux send --workspace $WS --surface $SF "실제 구현이 빠져있음. 다음 항목을 구현 후 DONE 재보고: [누락 항목]"
cmux send-key --workspace $WS --surface $SF enter
```

---

## Step 6: 코드 리뷰 (Agent 위임)

Main이 직접 리뷰하지 않는다. Sonnet agent에 위임:

```
Agent({
  subagent_type: "code-reviewer",
  model: "sonnet",
  run_in_background: true,
  prompt: "Review the changes in [worktree path]. Check for: ..."
})
```

> Opus + Opus 동시 실행 = 529 rate limit 위험. 리뷰는 반드시 Sonnet.

---

## Step 7: 병합 + 커밋

### 7-1. 워크트리 병합

```bash
# 각 워크트리의 변경사항 병합
git merge taskA-${ROUND} --no-edit
git merge taskB-${ROUND} --no-edit

# 충돌 시: Main이 직접 해결 (유일한 직접 코딩 예외)
```

### 7-2. GATE 체크리스트 (커밋 전 필수)

```
□ GATE 1: 모든 배정 surface DONE 확인
□ GATE 2: 코드 리뷰 Agent에 위임 완료
□ GATE 5: speckit 태스크 100% 완료
□ GATE 7: 워크트리 사용 + 병합 + 정리 (git worktree list에 /tmp/wt-* 0개)
□ LECEIPTS: 5-섹션 보고서 작성 (/tmp/cmux-leceipts-report.json)
□ 서브에이전트 리뷰 REJECT 항목 수정 완료
```

하나라도 미체크 → 커밋 차단.

### 7-3. 워크트리 정리

```bash
git worktree remove /tmp/wt-taskA-${ROUND}
git worktree remove /tmp/wt-taskB-${ROUND}
git branch -d taskA-${ROUND} taskB-${ROUND}
```

---

## Step 8: 커밋 + 보고

```bash
git add [modified files]
git commit -m "feat: [요약]"
```

사용자에게 최종 보고:
- 작업 내용 요약
- 수정된 파일 목록
- 리뷰 결과
- 잔여 위험

---

## 에러 복구

| 에러 | 감지 | 조치 |
|------|------|------|
| Rate limit (429) | `cmux read-screen`에서 감지 | 다른 surface로 재배정 |
| STALL (60s+) | 화면 변화 없음 | `cmux read-screen`으로 진단 → 재전송 |
| Context 초과 | "too long" 메시지 | `/new` 또는 `/clear` → 작업 분할 |
| sandbox 에러 | "Operation not permitted" | Main이 직접 처리 (예외) |

---

## 참조 문서

상세 프로토콜은 `references/` 디렉토리 참조:
- `dispatch-templates.md` — 디스패치 템플릿 + 팀장 프로토콜
- `gate-enforcement.md` — GATE 체크리스트 상세
- `worktree-workflow.md` — 워크트리 생명주기
- `cmux-commands-full.md` — cmux CLI 전체 레퍼런스
- `subagent-definitions.md` — 서브에이전트 역할 정의
