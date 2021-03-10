import json
from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from galaxy.webapps.galaxy.api.metrics import router


app = FastAPI()
app.include_router(router)


@pytest.mark.skip("WIP dependency resolve issue")
@pytest.mark.asyncio
async def test_request_create_metrics():
    payload = {
        "metrics": [
            {
                "namespace": "api-test",
                "time": f"{datetime.utcnow().isoformat()}Z",
                "level": 1,
                "args": json.dumps({
                    "arg01": "test"
                }),
            }
        ]
    }
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/metrics", json=payload)
        assert response.status_code == 200
