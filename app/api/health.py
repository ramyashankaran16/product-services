from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import get_health_service
from app.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health(service: HealthService = Depends(get_health_service)) -> JSONResponse:
    if service.database_is_up():
        return JSONResponse(status_code=200, content={"status": "UP", "database": "UP"})
    return JSONResponse(status_code=503, content={"status": "DOWN", "database": "DOWN"})
