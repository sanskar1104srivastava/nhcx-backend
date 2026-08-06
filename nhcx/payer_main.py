import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from nhcx.routers import payerRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="NHCX Payer Bridge")

# ponytail: wide open for local dev so the static frontend (any origin/port) can call this API.
# Restrict allow_origins before deploying anywhere public.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def logRequests(request: Request, call_next):
    logger.info("Incoming %s %s", request.method, request.url.path)
    return await call_next(request)

app.include_router(payerRouter.router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

# Lambda entrypoint
handler = Mangum(app)
