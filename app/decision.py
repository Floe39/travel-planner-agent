"""专家选择层：默认规则引擎可离线运行，LLM 接入作为可替换实现。"""
import json
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from openai import OpenAI

from .schemas import Activity, Flight, Hotel, TripRequest

T = TypeVar("T", Flight, Hotel, Activity)


@dataclass
class DecisionOutcome(Generic[T]):
    value: T
    fallback_reason: str | None = None


class DecisionEngine(Protocol):
    def choose_one(self, candidates: list[T], request: TripRequest) -> DecisionOutcome[T]: ...

    def choose_activities(self, candidates: list[Activity], request: TripRequest) -> DecisionOutcome[list[Activity]]: ...


class RuleDecisionEngine:
    """以显式评分替代黑盒选择；LLM 模式也必须通过后端预算校验。"""
    def choose_one(self, candidates: list[T], request: TripRequest) -> DecisionOutcome[T]:
        if request.preference == "economy":
            return DecisionOutcome(min(candidates, key=self._price))
        if request.preference == "comfort":
            return DecisionOutcome(max(candidates, key=self._comfort_score))
        return DecisionOutcome(sorted(candidates, key=lambda item: (self._price(item), -self._comfort_score(item)))[len(candidates) // 2])

    def choose_activities(self, candidates: list[Activity], request: TripRequest) -> DecisionOutcome[list[Activity]]:
        ranked = sorted(candidates, key=lambda item: item.price_per_person)
        return DecisionOutcome(ranked[:2] if request.preference == "economy" else [ranked[0], ranked[1], ranked[-1]])

    @staticmethod
    def _price(item: T) -> int:
        if isinstance(item, Flight):
            return item.price_per_person
        if isinstance(item, Hotel):
            return item.price_per_night
        return item.price_per_person

    @staticmethod
    def _comfort_score(item: T) -> float:
        if isinstance(item, Flight):
            return 10 - item.duration_hours
        if isinstance(item, Hotel):
            return item.rating
        return item.duration_hours


class LLMDecisionEngine:
    """让模型在受限候选集中选择，候选 ID 和预算仍由后端校验。"""
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.fallback = RuleDecisionEngine()

    def choose_one(self, candidates: list[T], request: TripRequest) -> DecisionOutcome[T]:
        selected_ids, fallback_reason = self._choose_ids(candidates, request, multiple=False)
        if selected_ids:
            return DecisionOutcome(next(item for item in candidates if item.id == selected_ids[0]))
        fallback = self.fallback.choose_one(candidates, request)
        return DecisionOutcome(fallback.value, fallback_reason)

    def choose_activities(self, candidates: list[Activity], request: TripRequest) -> DecisionOutcome[list[Activity]]:
        ids, fallback_reason = self._choose_ids(candidates, request, multiple=True)
        selected_ids = set(ids)
        selected = [item for item in candidates if item.id in selected_ids]
        if selected:
            return DecisionOutcome(selected)
        fallback = self.fallback.choose_activities(candidates, request)
        return DecisionOutcome(fallback.value, fallback_reason)

    def _choose_ids(self, candidates: list[T], request: TripRequest, multiple: bool) -> tuple[list[str], str | None]:
        prompt = {
            "task": "从候选中选择最符合旅行偏好的项目。只能返回候选 id，禁止编造。",
            "preference": request.preference,
            "destination": request.destination,
            "candidate_ids": [item.id for item in candidates],
            "candidates": [item.model_dump() for item in candidates],
            "output": '{"selected_ids":["candidate-id"]}',
            "rule": "活动可选 1 至 3 个；其他类型只选 1 个。" if multiple else "只选 1 个。",
        }
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "你是旅行规划专家，严格输出 JSON。"}, {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
                response_format={"type": "json_object"}, temperature=0,
            )
            payload = json.loads(response.choices[0].message.content or "{}")
            ids = payload.get("selected_ids", [])
            valid_ids = {item.id for item in candidates}
            ids = [item_id for item_id in ids if isinstance(item_id, str) and item_id in valid_ids]
            selected = ids[:3] if multiple else ids[:1]
            if not selected:
                return [], "LLM 返回了空结果或候选外 ID，已切换为规则引擎。"
            return selected, None
        except Exception:
            return [], "LLM 服务不可用或返回非法 JSON，已切换为规则引擎。"
