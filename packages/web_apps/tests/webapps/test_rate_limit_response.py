"""A hit rate limit is reported as a regular Galaxy error response."""

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from galaxy.webapps.galaxy.fast_app import (
    limiter,
    rate_limit_exceeded_handler,
)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.get("/limited")
@limiter.limit("1/minute")
async def limited(request: Request):
    return {"ok": True}


def test_rate_limited_request_is_a_galaxy_error_with_retry_after():
    client = TestClient(app)
    assert client.get("/limited").status_code == 200

    response = client.get("/limited")

    assert response.status_code == 429
    body = response.json()
    assert body["err_code"] == 429001
    assert body["err_msg"] == "Rate limit exceeded: 1 per 1 minute"
    assert 1 <= int(response.headers["Retry-After"]) <= 60
