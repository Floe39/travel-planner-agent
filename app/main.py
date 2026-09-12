import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .schemas import PlanResponse, TripRequest
from .service import TravelPlannerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
app = FastAPI(title="Travel Planner Agent API", version="0.1.0")
service = TravelPlannerService()


def error(code: str, message: str, request_id: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message, "request_id": request_id})


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_id=%s unhandled error", request_id)
        return error("INTERNAL_ERROR", "服务暂时不可用", request_id, 500)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_id=%s path=%s status=%s duration_ms=%d", request_id, request.url.path, response.status_code, (time.perf_counter() - started) * 1000)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    return error("VALIDATION_ERROR", exc.errors()[0]["msg"], request_id, 422)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/trips/plan", response_model=PlanResponse)
def create_plan(payload: TripRequest, request: Request) -> PlanResponse:
    return service.plan(payload, request.headers.get("X-Request-ID"))
