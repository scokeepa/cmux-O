# Branch Protection 설정 가이드

> 레포를 퍼블릭으로 전환한 후 적용할 보호 규칙.

## GitHub Free 플랜에서 사용 가능한 보호

퍼블릭 레포 전환 후 아래 명령을 실행:

```bash
# 1. main 브랜치 보호 활성화 (direct push 차단)
gh api repos/scokeepa/cmux-orchestrator-watcher-pack/rulesets \
  --method POST \
  --field name="main-protection" \
  --field target="branch" \
  --field enforcement="active" \
  --field conditions='{"ref_name":{"include":["refs/heads/main"],"exclude":[]}}' \
  --field rules='[
    {"type":"pull_request","parameters":{"required_approving_review_count":1,"dismiss_stale_reviews_on_push":true,"require_last_push_approval":false}},
    {"type":"required_status_checks","parameters":{"strict_status_checks_policy":true,"required_status_checks":[]}},
    {"type":"non_fast_forward"}
  ]' \
  --field bypass_actors='[{"actor_id":1,"actor_type":"OrganizationAdmin","bypass_mode":"always"}]'
```

## 또는 Web UI에서 설정

1. **Settings → Rules → Rulesets → New ruleset**
2. **Ruleset Name**: `main-protection`
3. **Target branches**: `main`
4. **Rules 활성화**:
   - ✅ Restrict deletions
   - ✅ Require a pull request before merging
     - Required approvals: 1
     - Dismiss stale reviews
   - ✅ Block force pushes

## 결과

| 행위 | 허용 여부 |
|------|----------|
| main 직접 push | ❌ 차단 |
| PR 생성 | ✅ 허용 |
| PR 머지 (승인 후) | ✅ 허용 |
| Issue 생성/업데이트 | ✅ 허용 |
| Force push | ❌ 차단 |
| Branch 삭제 (main) | ❌ 차단 |

## 퍼블릭 전환 명령

```bash
# 레포를 퍼블릭으로 전환
gh repo edit scokeepa/cmux-orchestrator-watcher-pack --visibility public

# 전환 후 위의 ruleset 명령 실행
```
