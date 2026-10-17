"""Unit tests for the Tasks API Lambda, using moto to fake DynamoDB (no AWS account needed).

Run:  pip install -r tests/requirements.txt && pytest -v
"""
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ["TABLE_NAME"] = "tasks-test"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import app  # noqa: E402


@pytest.fixture(autouse=True)
def dynamodb():
    with mock_aws():
        boto3.client("dynamodb").create_table(
            TableName="tasks-test",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        app._table = None
        yield
        app._table = None


def call(method, task_id=None, body=None):
    event = {
        "httpMethod": method,
        "path": "/tasks" + (f"/{task_id}" if task_id else ""),
        "pathParameters": {"id": task_id} if task_id else None,
        "body": body if isinstance(body, str) or body is None else json.dumps(body),
        "requestContext": {"requestId": "test"},
    }
    res = app.lambda_handler(event, None)
    return res["statusCode"], (json.loads(res["body"]) if res["body"] else None)


def test_create_and_get_task():
    status, task = call("POST", body={"title": "  Learn API Gateway  "})
    assert status == 201
    assert task["title"] == "Learn API Gateway"
    assert task["done"] is False

    status, fetched = call("GET", task["id"])
    assert status == 200
    assert fetched == task


def test_list_tasks_in_creation_order():
    call("POST", body={"title": "first"})
    call("POST", body={"title": "second"})
    status, tasks = call("GET")
    assert status == 200
    assert [t["title"] for t in tasks] == ["first", "second"]


def test_update_task():
    _, task = call("POST", body={"title": "write tests"})
    status, updated = call("PUT", task["id"], {"done": True})
    assert status == 200
    assert updated["done"] is True
    assert updated["title"] == "write tests"


def test_delete_task():
    _, task = call("POST", body={"title": "temporary"})
    assert call("DELETE", task["id"])[0] == 204
    assert call("GET", task["id"])[0] == 404
    assert call("DELETE", task["id"])[0] == 404


@pytest.mark.parametrize("body", [{}, {"title": ""}, {"title": 5}, {"title": "x" * 201},
                                  {"title": "ok", "done": "yes"}, "not json", "[1, 2]"])
def test_create_validation(body):
    status, err = call("POST", body=body)
    assert status == 400
    assert "message" in err


def test_update_missing_task_returns_404():
    assert call("PUT", "does-not-exist", {"done": True})[0] == 404


def test_update_requires_fields():
    _, task = call("POST", body={"title": "x"})
    assert call("PUT", task["id"], {})[0] == 400


def test_cors_headers_and_preflight():
    res = app.lambda_handler({"httpMethod": "OPTIONS", "pathParameters": None}, None)
    assert res["statusCode"] == 204
    assert res["headers"]["Access-Control-Allow-Origin"] == "*"


def test_unsupported_method():
    assert call("PATCH")[0] == 405
