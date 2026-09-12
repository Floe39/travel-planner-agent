from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TripRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=40)
    start_date: date
    end_date: date
    num_travelers: int = Field(ge=1, le=8)
    budget: int = Field(ge=500, le=100_000, description="总预算，单位：元")
    preference: Literal["balanced", "comfort", "economy"] = "balanced"

    @model_validator(mode="after")
    def validate_dates(self) -> "TripRequest":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be later than start_date")
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("trip duration must not exceed 30 days")
        return self


class Flight(BaseModel):
    id: str
    airline: str
    departure: str
    arrival: str
    price_per_person: int
    duration_hours: float


class Hotel(BaseModel):
    id: str
    name: str
    rating: float
    price_per_night: int
    amenities: list[str]


class Activity(BaseModel):
    id: str
    name: str
    duration_hours: float
    price_per_person: int


class BudgetBreakdown(BaseModel):
    flights: int
    hotel: int
    activities: int
    total: int
    budget: int
    remaining: int


class PlanResponse(BaseModel):
    request_id: str
    status: Literal["success", "budget_unmet"]
    destination: str
    nights: int
    flight: Flight
    hotel: Hotel
    activities: list[Activity]
    budget_breakdown: BudgetBreakdown
    plan_summary: str
    replan_count: int
    minimum_available_budget: int | None = None
    adjustment_suggestions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
