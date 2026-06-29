# github_actions_lab

GitHub Actions를 활용한 CI/CD 파이프라인 실습 프로젝트.

## 기술 스택

| 항목 | 선택 |
|------|------|
| 앱 | Python 3.12 + FastAPI |
| 테스트 | pytest |
| 린팅 | ruff + black |
| 컨테이너 | Docker + GHCR |
| 배포 | Render |
| 브랜치 전략 | GitHub Flow |

## CI/CD 파이프라인

### CI — Pull Request → main

| Job | 내용 |
|-----|------|
| lint | ruff + black |
| test (3.11) | pytest |
| test (3.12) | pytest |

세 개 모두 통과해야 머지 가능. Branch Protection Rule로 강제.

### CD — main push

| Job | 내용 | 방식 |
|-----|------|------|
| build | Docker 이미지 빌드 + GHCR push | 자동 |
| deploy-staging | Render staging 배포 | 자동 |
| deploy-production | Render production 배포 | 수동 승인 후 실행 |

## 로컬 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (핫 리로드)
uvicorn app.main:app --reload

# 테스트
pytest -v

# 린팅
ruff check .
black --check .
```

## 디렉터리 구조

```
github_actions_lab/
├── app/
│   ├── main.py
│   └── routers/
│       └── health.py
├── tests/
│   └── test_health.py
├── Dockerfile
├── requirements.txt
└── .github/
    ├── actions/
    │   └── setup-python-env/
    │       └── action.yml
    ├── labeler.yml
    └── workflows/
        ├── reusable-ci.yml
        ├── ci.yml
        ├── cd.yml
        └── labeler.yml
```
