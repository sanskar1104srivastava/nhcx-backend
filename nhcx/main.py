import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from nhcx.routers import receiverRouter, senderRouter, testRouter, logsRouter, sandboxToolsRouter, payerRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="NHCX Provider Bridge")

# ponytail: wide open for local dev so the static frontend (any origin/port) can call this API.
# Restrict allow_origins before deploying anywhere public.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def logRequests(request: Request, call_next):
    logger.info("Incoming %s %s", request.method, request.url.path)
    return await call_next(request)


# No startup-time table creation here — the table is provisioned by serverless.yml's
# CloudFormation resources, and the Lambda role is deliberately scoped to PutItem/GetItem/Query
# only (least privilege). DescribeTable/CreateTable aren't granted, so calling this at runtime
# would just AccessDeniedException. Local dev uses run_local.py's explicit preflight instead.


app.include_router(senderRouter.router)
app.include_router(receiverRouter.router)
app.include_router(testRouter.router)
app.include_router(logsRouter.router)
app.include_router(sandboxToolsRouter.router)
app.include_router(payerRouter.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.api_route("/", methods=["GET", "POST", "HEAD"])
def root() -> dict:
    """NHCX appears to probe the bare registered endpoint_url (reachability check) before
    attempting the real callback on an entity-specific path — confirmed via the sandbox
    retrying POST / every ~60s and getting FastAPI's default 404 for an unmatched route,
    which silently killed every inbound callback. Any 200 here is enough to satisfy that."""
    return {"status": "ok"}


# Lambda entrypoint — one image per module, FastAPI routes GET/POST/etc inside it.
handler = Mangum(app)
