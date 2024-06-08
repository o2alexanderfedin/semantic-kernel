import os
from unittest.mock import patch

import pytest
import yaml
from openapi_core import Spec

from semantic_kernel.connectors.openapi_plugin.openapi_function_execution_parameters import (
    OpenAPIFunctionExecutionParameters,
)
from semantic_kernel.connectors.openapi_plugin.openapi_manager import (
    OpenApiParser,
    OpenApiRunner,
    RestApiOperation,
)

directory = os.path.dirname(os.path.realpath(__file__))
openapi_document = directory + "/openapi.yaml"
invalid_openapi_document = directory + "/invalid_openapi.yaml"
with open(openapi_document) as f:
    openapi_document_json = yaml.safe_load(f)
spec = Spec.from_dict(openapi_document_json)

operation_names = [
    "getTodos",
    "addTodo",
    "getTodoById",
    "updateTodoById",
    "deleteTodoById",
]

put_operation = RestApiOperation(
    id="updateTodoById",
    method="PUT",
    server_url="http://example.com",
    path="/todos/{id}",
    summary="Update a todo by ID",
    params=[
        {
            "name": "id",
            "in": "path",
            "required": True,
            "schema": {"type": "integer", "minimum": 1},
        },
        {
            "name": "Authorization",
            "in": "header",
            "required": True,
            "schema": {"type": "string", "description": "The authorization token"},
        },
        {
            "name": "completed",
            "in": "query",
            "required": False,
            "schema": {
                "type": "boolean",
                "description": "Whether the todo is completed or not",
            },
        },
    ],
    request_body={
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the todo",
                            "example": "Buy milk",
                        },
                        "completed": {
                            "type": "boolean",
                            "description": "Whether the todo is completed or not",
                            "example": False,
                        },
                    },
                }
            }
        },
    },
)


"""OpenApiParser tests"""


def test_parse_valid():
    parser = OpenApiParser()
    result = parser.parse(openapi_document)
    assert result == spec.content()


def test_parse_invalid_location():
    parser = OpenApiParser()
    with pytest.raises(Exception):
        parser.parse("invalid_location")


def test_parse_invalid_format():
    parser = OpenApiParser()
    with pytest.raises(Exception):
        parser.parse(invalid_openapi_document)


@pytest.fixture
def openapi_runner():
    parser = OpenApiParser()
    parsed_doc = parser.parse(openapi_document)
    operations = parser.create_rest_api_operations(parsed_doc)
    runner = OpenApiRunner(parsed_openapi_document=parsed_doc)
    return runner, operations


@pytest.fixture
def openapi_runner_with_url_override():
    parser = OpenApiParser()
    parsed_doc = parser.parse(openapi_document)
    exec_settings = OpenAPIFunctionExecutionParameters(server_url_override="http://urloverride.com")
    operations = parser.create_rest_api_operations(parsed_doc, execution_settings=exec_settings)
    runner = OpenApiRunner(parsed_openapi_document=parsed_doc)
    return runner, operations


@pytest.fixture
def openapi_runner_with_auth_callback():
    async def dummy_auth_callback(**kwargs):
        return {"Authorization": "Bearer dummy-token"}

    parser = OpenApiParser()
    parsed_doc = parser.parse(openapi_document)
    exec_settings = OpenAPIFunctionExecutionParameters(server_url_override="http://urloverride.com")
    operations = parser.create_rest_api_operations(parsed_doc, execution_settings=exec_settings)
    runner = OpenApiRunner(
        parsed_openapi_document=parsed_doc,
        auth_callback=dummy_auth_callback,
    )
    return runner, operations


@patch("aiohttp.ClientSession.request")
@pytest.mark.asyncio
async def test_run_operation_with_invalid_request(mock_request, openapi_runner):
    runner, operations = openapi_runner
    operation = operations["getTodoById"]
    headers = {"Authorization": "Bearer abc123"}
    request_body = {"title": "Buy milk"}
    mock_request.return_value.__aenter__.return_value.text.return_value = 400
    with pytest.raises(Exception):
        await runner.run_operation(operation, headers=headers, request_body=request_body)


@patch("aiohttp.ClientSession.request")
@pytest.mark.asyncio
async def test_run_operation_with_error(mock_request, openapi_runner):
    runner, operations = openapi_runner
    operation = operations["addTodo"]
    headers = {"Authorization": "Bearer abc123"}
    request_body = {"title": "Buy milk", "completed": False}
    mock_request.side_effect = Exception("Error")
    with pytest.raises(Exception):
        await runner.run_operation(operation, headers=headers, request_body=request_body)
