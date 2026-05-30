from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.users.interfaces.api.router import router as users_router

app = FastAPI(title="CanTelcoX Identity Service API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|10\.0\.2\.2|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "identity-service"}
