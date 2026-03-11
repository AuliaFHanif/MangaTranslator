import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    lmstudio_connected: bool
    lmstudio_url: str

@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    lmstudio_url = f"http://{settings.lmstudio_host}:{settings.lmstudio_port}"
    connected = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{lmstudio_url}/v1/models")
            connected = resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        connected = False
    return HealthResponse(status="ok", lmstudio_connected=connected, lmstudio_url=lmstudio_url)
