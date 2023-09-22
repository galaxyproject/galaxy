from typing import List

from fastapi.applications import FastAPI
from fastapi.param_functions import (
    Depends,
    Query,
)
from fastapi.testclient import TestClient

from galaxy.webapps.galaxy.api.common import query_parameter_as_list

app = FastAPI()

client = TestClient(app)


@app.get("/test/get_value_as_list")
async def get_value_as_list(
    values: List[str] = Depends(query_parameter_as_list(Query(alias="value"))),
):
    return values


def test_single_value():
    query_params = "value=val"
    result = _get_result_for_params(query_params)
    assert len(result) == 1
    assert result[0] == "val"


def test_list_as_comma_separated_values():
    query_params = "value=val1,val2,val3"
    result = _get_result_for_params(query_params)

    assert len(result) == 3
    assert result[0] == "val1"
    assert result[1] == "val2"
    assert result[2] == "val3"


def test_list_as_multiple_query_entries():
    query_params = "value=val1&value=val2&value=val3"
    result = _get_result_for_params(query_params)

    assert len(result) == 3
    assert result[0] == "val1"
    assert result[1] == "val2"
    assert result[2] == "val3"


def _get_result_for_params(query_params: str):
    response = client.get(f"/test/get_value_as_list?{query_params}")

    assert response.status_code == 200
    result = response.json()
    return result
