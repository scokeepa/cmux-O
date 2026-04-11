# AI Profiles

> 6 AI 모델 자동 감지, 역할 배정, 프로파일 관리.

## 지원 AI

| AI | CLI | 강점 | 적합 역할 |
|----|-----|------|-----------|
| **Claude** | `claude` | 범용, 고품질 | Boss, Lead |
| **Codex** | `codex` | 빠른 코딩, 샌드박스 | Worker |
| **OpenCode** | `cco` | 경량, 고속 | Worker |
| **GLM** | `ccg2` | 짧은 프롬프트 전문 | Worker (< 200자) |
| **Gemini** | `gemini` | 2단계 전달 | Worker |
| **MiniMax** | `ccm` | 균형, 비용 효율 | Worker |

## 관리 명령

```bash
/cmux-config detect     # PATH에서 AI CLI 자동 감지
/cmux-config add codex   # 수동 추가
/cmux-config remove glm  # 수동 제거
```

## SSOT

런타임 AI 가용성은 `shutil.which(cli_command)`로 판정한다. `ai-profile.json`의 `detected` 필드는 캐시일 뿐이다.
