from fastapi import APIRouter

api_router = APIRouter(
    tags=["Ping"],
)


@api_router.get("/ping")
def ping():
    return {
        "message": "pong"
    }