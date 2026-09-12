from datetime import date

from app.decision import LLMDecisionEngine
from app.schemas import Flight, TripRequest


class BrokenClient:
    class Chat:
        class Completions:
            @staticmethod
            def create(**_):
                raise TimeoutError("simulated model timeout")

        completions = Completions()

    chat = Chat()


def test_llm_failure_is_exposed_and_uses_rule_fallback():
    request = TripRequest(destination="东京", start_date=date(2026, 10, 1), end_date=date(2026, 10, 3), num_travelers=1, budget=5_000, preference="economy")
    candidates = [
        Flight(id="expensive", airline="A", departure="08:00", arrival="12:00", price_per_person=1000, duration_hours=4),
        Flight(id="cheap", airline="B", departure="09:00", arrival="14:00", price_per_person=500, duration_hours=5),
    ]
    engine = LLMDecisionEngine("test-key", "https://example.invalid", "test-model")
    engine.client = BrokenClient()

    outcome = engine.choose_one(candidates, request)

    assert outcome.value.id == "cheap"
    assert outcome.fallback_reason and "已切换为规则引擎" in outcome.fallback_reason
