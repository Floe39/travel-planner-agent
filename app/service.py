import uuid

from .config import get_settings
from .decision import LLMDecisionEngine, RuleDecisionEngine
from .graph import create_planner_graph
from .schemas import PlanResponse, TripRequest


class TravelPlannerService:
    def __init__(self):
        settings = get_settings()
        settings.require_llm_credentials()
        engine: RuleDecisionEngine | LLMDecisionEngine = RuleDecisionEngine()
        if settings.planner_mode == "llm":
            engine = LLMDecisionEngine(settings.openai_api_key, settings.openai_base_url, settings.openai_model)
        self.graph = create_planner_graph(engine=engine)

    def plan(self, request: TripRequest, request_id: str | None = None) -> PlanResponse:
        state = self.graph.invoke({"request": request, "replan_count": 0})
        return PlanResponse(
            request_id=request_id or str(uuid.uuid4()),
            destination=state["request"].destination,
            nights=(state["request"].end_date - state["request"].start_date).days,
            flight=state["selected_flight"], hotel=state["selected_hotel"], activities=state["selected_activities"],
            budget_breakdown=state["budget_breakdown"], plan_summary=state["plan_summary"],
            status=state["plan_status"], replan_count=state.get("replan_count", 0),
            minimum_available_budget=state.get("minimum_available_budget"), adjustment_suggestions=state.get("adjustment_suggestions", []),
            warnings=list(dict.fromkeys(state.get("warnings", []))),
        )
