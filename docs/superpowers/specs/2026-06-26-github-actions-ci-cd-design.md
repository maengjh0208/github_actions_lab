# GitHub Actions CI/CD 실습 설계

**날짜:** 2026-06-26
**스택:** Python (FastAPI) + Docker + GHCR + Render
**브랜치 전략:** GitHub Flow (main 단일 상용 브랜치)
**목표:** 개인 실습 수준을 넘어 팀 단위 실무 패턴을 단계적으로 체험

---

## 전체 구조

총 6개 Phase를 순서대로 진행하며, 각 Phase는 이전 Phase 위에 레이어를 쌓는 방식으로 설계됨. 마지막 Phase 완료 시 실무 팀이 쓰는 파이프라인 구조와 동일해짐.

```
Phase 1  GitHub Actions 기초 + 첫 번째 CI
Phase 2  실전 CI 파이프라인 (품질 검사, 캐시, 매트릭스)
Phase 3  Branch 전략 + PR 자동화
Phase 4  CD — Render 자동 배포
Phase 5  Environments + 수동 승인 게이트 (staging → production)
Phase 6  Reusable Workflows — 팀 표준 구조 완성
```

---

## Phase 1: GitHub Actions 기초 + 첫 번째 CI

### 목표
Actions가 어떻게 동작하는지 내부 구조를 이해하고, 실제 FastAPI 앱에 첫 CI를 붙인다.

### 핵심 개념
| 용어 | 설명 |
|------|------|
| Workflow | Event가 발생하면 실행되는 자동화 단위 (.yml 파일) |
| Job | Workflow 안의 독립 실행 단위 (각각 별도 Runner에서 실행) |
| Step | Job 안의 순서대로 실행되는 명령어 or Action |
| Runner | Step을 실행하는 서버 (GitHub이 제공하는 ubuntu-latest 등) |
| Event | push, pull_request, workflow_dispatch 등 트리거 |

### 디렉터리 구조
```
github_actions_lab/
├── app/
│   ├── main.py
│   └── routers/
│       └── health.py
├── tests/
│   └── test_health.py
├── requirements.txt
└── .github/
    └── workflows/
        └── ci.yml
```

### 첫 워크플로우
```yaml
# .github/workflows/ci.yml
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: pytest
```

### 실습 체크포인트
- Actions 탭에서 실행 로그 보는 법
- Job/Step 별 실행 시간 확인
- 테스트 실패 시 워크플로우 표시 방식 확인

---

## Phase 2: 실전 CI 파이프라인

### 목표
"테스트만 돌리는 CI"에서 "팀이 실제 쓰는 CI"로 업그레이드. 속도, 품질, 호환성을 동시에 잡는다.

### Job 구조
```
CI Workflow
├── lint        (ruff + black)  ──┐
└── test                          ├── 병렬 실행
    ├── python 3.11  ─────────────┤
    └── python 3.12  ─────────────┘
```

### 주요 패턴

**캐시로 속도 최적화**
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```
`requirements.txt`가 바뀌지 않으면 캐시 재사용 → 빌드 시간 60~70% 단축.

**Matrix Build**
```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```
설정 하나로 Job이 2개로 분기되어 병렬 실행.

### 실습 체크포인트
- 캐시 hit/miss 로그 확인
- Matrix Job이 Actions 탭에서 어떻게 보이는지
- lint 실패 vs test 실패 분리 표시 확인
- Coverage 리포트를 Artifacts로 저장 및 다운로드

---

## Phase 3: Branch 전략 + PR 자동화

### 목표
혼자 쓰는 CI에서 팀이 쓰는 CI로 전환. 브랜치마다 다른 규칙이 적용되고, PR이 열리면 자동으로 일이 일어나는 구조.

### 브랜치 전략 (GitHub Flow)
```
main        →  항상 배포 가능한 상태. 직접 push 금지.
feature/*   →  기능 개발. PR을 통해서만 main에 병합 가능.
hotfix/*    →  긴급 수정. PR 필수.
```

| 이벤트 | 실행 내용 |
|--------|-----------|
| feature/* push | lint + test |
| PR to main | lint + test + 추가 검사 |
| main push | CI + CD 트리거 |

### Branch Protection Rules (GitHub 설정)
```
✅ Require a pull request before merging
✅ Require status checks to pass
✅ Require branches to be up to date before merging
✅ Restrict who can push to matching branches
```

### PR 자동 라벨링
```yaml
# .github/labeler.yml
feature:
  - head-branch: ["^feature/"]
hotfix:
  - head-branch: ["^hotfix/"]
```

### PR 테스트 결과 자동 코멘트
```
PR 코멘트 자동 예시:
┌─────────────────────────────┐
│ ✅ CI Results               │
│ Tests passed: 12/12         │
│ Coverage: 87%               │
│ Lint: passed                │
└─────────────────────────────┘
```
`pytest-junit` + `github-script` Action 조합으로 구현.

### 실습 체크포인트
- `feature/add-user-api` 브랜치 → PR → 라벨 자동 부착 확인
- CI 실패 상태에서 머지 버튼 비활성화 확인
- PR 코멘트에 테스트 결과 자동 게시 확인

---

## Phase 4: CD — Render 자동 배포

### 목표
`main`에 머지되는 순간 자동으로 Render에 배포가 일어나는 구조. CI 통과 코드만 배포.

### 전체 흐름
```
feature/* PR 오픈
    → CI 실행 (lint + test)
    → 성공 시 머지 가능
    → main 브랜치 업데이트
    → CD 워크플로우 트리거
    → Docker 이미지 빌드
    → GHCR 푸시
    → Render 배포 트리거 (Deploy Hook)
```

### 이미지 태깅 전략
```
ghcr.io/username/repo:a3f8c2d   # 커밋 SHA (추적 가능)
ghcr.io/username/repo:latest    # 항상 최신
```
두 태그를 동시에 붙이는 것이 팀 표준. SHA로 현재 배포 버전 역추적 가능.

### Secrets 등록
```
GitHub 레포 → Settings → Secrets and variables → Actions
RENDER_DEPLOY_HOOK_URL  →  Render에서 발급받은 웹훅 URL
```

### 실습 체크포인트
- PR 머지 → CD 워크플로우 자동 실행 확인
- GHCR에 이미지 확인 (레포 → Packages 탭)
- Render 대시보드에서 배포 로그 확인
- 실제 URL에서 `/health` 엔드포인트 접속 확인
- 의도적 실패 커밋 → CI 실패 → CD 미실행 확인

---

## Phase 5: Environments + 수동 승인 게이트

### 목표
staging → production 순서로 배포가 흘러가고, production 배포 전에 사람이 승인해야 하는 구조.

### 배포 흐름
```
main 머지
    → build (Docker 이미지 빌드 + GHCR 푸시)
    → deploy-staging (자동)
    → deploy-production (승인 대기 → 승인 시 실행)
```

### GitHub Environments 설정
```
Environment: staging
  - 보호 규칙: 없음 (자동 배포)
  - Secrets: RENDER_STAGING_DEPLOY_HOOK_URL
  - Vars: DATABASE_URL (staging DB), LOG_LEVEL=debug

Environment: production
  - 보호 규칙: Required reviewers 설정
  - Secrets: RENDER_PRODUCTION_DEPLOY_HOOK_URL
  - Vars: DATABASE_URL (prod DB), LOG_LEVEL=warning
```

### 환경별 Secrets 분리
같은 변수명(`DATABASE_URL`)이지만 Environment에 따라 다른 값이 주입됨. 코드 변경 없이 환경 분리.

### 실습 체크포인트
- staging 자동 배포 + production 대기 상태 직접 확인
- Actions 탭에서 승인 버튼으로 production 배포 트리거
- 거부 시 워크플로우 표시 확인
- staging URL vs production URL 다른 값 반환 확인

---

## Phase 6: Reusable Workflows — 팀 표준 구조 완성

### 목표
복사해서 쓰는 워크플로우에서 공통 컴포넌트를 가져다 쓰는 구조로 전환. 레포가 여러 개인 팀에서 CI/CD 표준을 유지하는 방법 체험.

### Reusable Workflow (`workflow_call`)
```yaml
# .github/workflows/reusable-ci.yml
on:
  workflow_call:
    inputs:
      python-version:
        type: string
        default: "3.12"
    secrets:
      RENDER_DEPLOY_HOOK_URL:
        required: true
```

```yaml
# .github/workflows/ci.yml (호출하는 쪽)
jobs:
  ci:
    uses: ./.github/workflows/reusable-ci.yml
    with:
      python-version: "3.12"
    secrets: inherit
```

### Composite Actions
여러 Step을 하나의 Action으로 묶어 재사용:
```
.github/actions/setup-python-env/action.yml
→ Python 설치 + 캐시 설정 + pip install 을 한 줄로
```

### 최종 완성 디렉터리 구조
```
.github/
├── actions/
│   └── setup-python-env/
│       └── action.yml
└── workflows/
    ├── reusable-ci.yml
    ├── reusable-cd.yml
    ├── ci.yml
    ├── cd.yml
    └── labeler.yml
```

### 실습 체크포인트
- `ci.yml`이 단 몇 줄로 줄어드는 것 확인
- Reusable workflow input으로 Python 버전 변경 테스트
- Composite Action으로 반복 코드 제거 리팩터링
- Phase 1~5 전체 파이프라인이 하나로 통합된 구조 감상

---

## 기술 스택 요약

| 항목 | 선택 |
|------|------|
| 앱 | Python 3.12 + FastAPI |
| 테스트 | pytest + pytest-cov |
| 린팅 | ruff + black |
| 컨테이너 | Docker + GHCR |
| 배포 | Render (무료 티어) |
| 브랜치 전략 | GitHub Flow |
| CI 트리거 | push (feature/*), pull_request (→ main) |
| CD 트리거 | push (main) |
