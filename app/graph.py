from operator import add
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from .decision import DecisionEngine, RuleDecisionEngine
from .schemas import Activity, BudgetBreakdown, Flight, Hotel, TripRequest
from .tools import MockTravelDataProvider


class PlannerState(TypedDict, total=False):
    request: TripRequest
    flights: list[Flight]
    hotels: list[Hotel]
    activities_catalog: list[Activity]
    selected_flight: Flight
    selected_hotel: Hotel
    selected_activities: list[Activity]
    budget_breakdown: BudgetBreakdown
    replan_count: int
    warnings: Annotated[list[str], add]
    plan_summary: str
    plan_status: Literal["success", "budget_unmet"]
    minimum_available_budget: int | None
    adjustment_suggestions: list[str]


def create_planner_graph(provider: MockTravelDataProvider | None = None, engine: DecisionEngine | None = None):
    provider = provider or MockTravelDataProvider()
    engine = engine or RuleDecisionEngine()

    def flight_expert(state: PlannerState) -> dict:
        request = state["request"]
        candidates = provider.search_flights(request)
        outcome = engine.choose_one(candidates, request)
        return {"flights": candidates, "selected_flight": outcome.value, "warnings": [outcome.fallback_reason] if outcome.fallback_reason else []}

    def hotel_expert(state: PlannerState) -> dict:
        request = state["request"]
        candidates = provider.search_hotels(request)
        outcome = engine.choose_one(candidates, request)
        return {"hotels": candidates, "selected_hotel": outcome.value, "warnings": [outcome.fallback_reason] if outcome.fallback_reason else []}

    def activity_expert(state: PlannerState) -> dict:
        request = state["request"]
        candidates = provider.search_activities(request)
        outcome = engine.choose_activities(candidates, request)
        return {"activities_catalog": candidates, "selected_activities": outcome.value, "warnings": [outcome.fallback_reason] if outcome.fallback_reason else []}

    def calculate_budget(state: PlannerState) -> dict:
        request = state["request"]
        nights = (request.end_date - request.start_date).days
        flights = state["selected_flight"].price_per_person * request.num_travelers
        hotel = state["selected_hotel"].price_per_night * nights
        activities = sum(item.price_per_person for item in state["selected_activities"]) * request.num_travelers
        total = flights + hotel + activities
        return {"budget_breakdown": BudgetBreakdown(flights=flights, hotel=hotel, activities=activities, total=total, budget=request.budget, remaining=request.budget - total)}

    def decide_next(state: PlannerState) -> str:
        if state["budget_breakdown"].total <= state["request"].budget:
            return "compose"
        if state.get("replan_count", 0) == 0:
            return "reduce_activities"
        if state.get("replan_count", 0) == 1:
            return "reduce_hotel"
        if state.get("replan_count", 0) == 2:
            return "reduce_flight"
        return "compose"

    def reduce_activities(state: PlannerState) -> dict:
        cheapest = min(state["activities_catalog"], key=lambda item: item.price_per_person)
        return {"selected_activities": [cheapest], "replan_count": 1, "warnings": ["初始方案超出预算，已先缩减活动安排并重新核算。"]}

    def reduce_hotel(state: PlannerState) -> dict:
        cheapest = min(state["hotels"], key=lambda item: item.price_per_night)
        return {"selected_hotel": cheapest, "replan_count": 2, "warnings": ["缩减活动后仍超预算，已切换为更低价酒店并重新核算。"]}

    def reduce_flight(state: PlannerState) -> dict:
        cheapest = min(state["flights"], key=lambda item: item.price_per_person)
        return {"selected_flight": cheapest, "replan_count": 3, "warnings": ["更换酒店后仍超预算，已切换为更低价航班并重新核算。"]}

    def compose_plan(state: PlannerState) -> dict:
        request = state["request"]
        budget = state["budget_breakdown"]
        activity_names = "、".join(item.name for item in state["selected_activities"])
        is_feasible = budget.total <= request.budget
        suggestions = [] if is_feasible else [f"将总预算至少提高到 {budget.total} 元（当前还差 {budget.total - request.budget} 元）。", "缩短住宿天数或减少出行人数后重新规划。"]
        warnings = [] if is_feasible else ["已尝试缩减活动、更换酒店和航班，当前 Mock 候选中仍无满足预算的方案。"]
        return {"warnings": warnings, "plan_status": "success" if is_feasible else "budget_unmet", "minimum_available_budget": None if is_feasible else budget.total, "adjustment_suggestions": suggestions, "plan_summary": f"{request.destination} {request.num_travelers} 人行程：选择{state['selected_flight'].airline}、{state['selected_hotel'].name}，安排{activity_names}；预计总花费 {budget.total} 元。"}

    graph = StateGraph(PlannerState)
    graph.add_node("flight_expert", flight_expert)
    graph.add_node("hotel_expert", hotel_expert)
    graph.add_node("activity_expert", activity_expert)
    graph.add_node("calculate_budget", calculate_budget)
    graph.add_node("reduce_activities", reduce_activities)
    graph.add_node("reduce_hotel", reduce_hotel)
    graph.add_node("reduce_flight", reduce_flight)
    graph.add_node("compose_plan", compose_plan)
    graph.add_edge(START, "flight_expert")
    graph.add_edge(START, "hotel_expert")
    graph.add_edge(START, "activity_expert")
    graph.add_edge(["flight_expert", "hotel_expert", "activity_expert"], "calculate_budget")
    graph.add_conditional_edges("calculate_budget", decide_next, {"reduce_activities": "reduce_activities", "reduce_hotel": "reduce_hotel", "reduce_flight": "reduce_flight", "compose": "compose_plan"})
    graph.add_edge("reduce_activities", "calculate_budget")
    graph.add_edge("reduce_hotel", "calculate_budget")
    graph.add_edge("reduce_flight", "calculate_budget")
    graph.add_edge("compose_plan", END)
    return graph.compile()
