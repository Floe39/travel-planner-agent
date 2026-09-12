from datetime import date

from app.schemas import TripRequest
from app.service import TravelPlannerService


def trip(**overrides) -> TripRequest:
    data = {"destination": "东京", "start_date": date(2026, 10, 1), "end_date": date(2026, 10, 5), "num_travelers": 2, "budget": 20_000, "preference": "comfort"}
    data.update(overrides)
    return TripRequest(**data)


def test_planner_returns_a_valid_plan_within_budget():
    result = TravelPlannerService().plan(trip())
    assert result.status == "success"
    assert result.budget_breakdown.total <= result.budget_breakdown.budget
    assert result.replan_count == 0
    assert result.nights == 4


def test_planner_replans_when_first_plan_exceeds_budget():
    result = TravelPlannerService().plan(trip(budget=4_000))
    assert result.status == "success"
    assert result.replan_count == 2
    assert result.budget_breakdown.total <= result.budget_breakdown.budget
    assert any("缩减活动" in warning for warning in result.warnings)


def test_planner_returns_budget_unmet_after_all_replanning_options_are_used():
    result = TravelPlannerService().plan(trip(budget=2_500))
    assert result.status == "budget_unmet"
    assert result.replan_count == 3
    assert result.minimum_available_budget == result.budget_breakdown.total
    assert result.minimum_available_budget > result.budget_breakdown.budget
    assert result.adjustment_suggestions


def test_end_date_must_be_after_start_date():
    try:
        trip(start_date=date(2026, 10, 5), end_date=date(2026, 10, 5))
    except ValueError as exc:
        assert "end_date" in str(exc)
    else:
        raise AssertionError("expected date validation error")
