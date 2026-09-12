"""保持测试简单：不依赖 TestClient，只验证路由处理函数的输入和输出契约。"""
from starlette.requests import Request

from app.main import create_plan, health
from app.schemas import TripRequest


def fake_request(request_id: str = "test-request-id") -> Request:
    return Request({"type": "http", "method": "POST", "path": "/api/trips/plan", "headers": [(b"x-request-id", request_id.encode())]})


def test_health_endpoint():
    assert health() == {"status": "ok"}


def test_plan_endpoint_returns_budget_unmet_status():
    payload = TripRequest(destination="东京", start_date="2026-10-01", end_date="2026-10-05", num_travelers=2, budget=2500, preference="comfort")
    response = create_plan(payload, fake_request())
    assert response.request_id == "test-request-id"
    assert response.status == "budget_unmet"
