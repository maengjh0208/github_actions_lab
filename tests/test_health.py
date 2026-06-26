# TestClient는 실제 서버를 띄우지 않고 FastAPI 앱에 HTTP 요청을 보낼 수 있게 해주는 도구. httpx 기반으로 동작.

from fastapi.testclient import TestClient
from app.main import app  # main.py 에서 만든 FastAPI 인스턴스

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
