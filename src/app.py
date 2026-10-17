"""Tasks API: a Lambda function behind Amazon API Gateway (REST API, Lambda proxy integration).

Routes
  GET    /tasks             list all tasks
  POST   /tasks             create a task          body: {"title": "...", "done": false}
  GET    /tasks/{id}        get one task
  PUT    /tasks/{id}        update a task          body: {"title": "...", "done": true}
  DELETE /tasks/{id}        delete a task
"""
import json
import os
import uuid
from datetime import datetime, timezone

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "tasks")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

_table = None


def table():
    """Create the DynamoDB table client lazily (reused across warm invocations)."""
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(TABLE_NAME)
    return _table


def response(status, body=None):
    """Build the response shape API Gateway's Lambda proxy integration expects."""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Headers": "Content-Type,x-api-key",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": "" if body is None else json.dumps(body),
    }


def parse_body(event):
    try:
        data = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return None, "Body must be valid JSON"
    if not isinstance(data, dict):
        return None, "Body must be a JSON object"
    return data, None


def validate(data, partial=False):
    """Return an error message, or None if the payload is valid."""
    if not partial or "title" in data:
        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            return "'title' is required and must be a non-empty string"
        if len(title) > 200:
            return "'title' must be 200 characters or fewer"
    if "done" in data and not isinstance(data["done"], bool):
        return "'done' must be true or false"
    return None


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def list_tasks():
    items = table().scan().get("Items", [])
    items.sort(key=lambda t: t["createdAt"])
    return response(200, items)


def create_task(event):
    data, err = parse_body(event)
    if err or (err := validate(data)):
        return response(400, {"message": err})
    task = {
        "id": str(uuid.uuid4()),
        "title": data["title"].strip(),
        "done": data.get("done", False),
        "createdAt": now(),
    }
    task["updatedAt"] = task["createdAt"]
    table().put_item(Item=task)
    return response(201, task)


def get_task(task_id):
    item = table().get_item(Key={"id": task_id}).get("Item")
    if not item:
        return response(404, {"message": f"Task {task_id} not found"})
    return response(200, item)


def update_task(task_id, event):
    data, err = parse_body(event)
    if err or (err := validate(data, partial=True)):
        return response(400, {"message": err})
    fields = {k: data[k] for k in ("title", "done") if k in data}
    if not fields:
        return response(400, {"message": "Provide 'title' and/or 'done'"})
    if "title" in fields:
        fields["title"] = fields["title"].strip()
    fields["updatedAt"] = now()

    names = {f"#{k}": k for k in fields}
    values = {f":{k}": v for k, v in fields.items()}
    try:
        result = table().update_item(
            Key={"id": task_id},
            UpdateExpression="SET " + ", ".join(f"#{k} = :{k}" for k in fields),
            ConditionExpression="attribute_exists(id)",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
    except table().meta.client.exceptions.ConditionalCheckFailedException:
        return response(404, {"message": f"Task {task_id} not found"})
    return response(200, result["Attributes"])


def delete_task(task_id):
    try:
        table().delete_item(Key={"id": task_id}, ConditionExpression="attribute_exists(id)")
    except table().meta.client.exceptions.ConditionalCheckFailedException:
        return response(404, {"message": f"Task {task_id} not found"})
    return response(204)


def lambda_handler(event, context):
    method = event.get("httpMethod")
    task_id = (event.get("pathParameters") or {}).get("id")
    print(json.dumps({"method": method, "path": event.get("path"), "requestId": event.get("requestContext", {}).get("requestId")}))

    if method == "OPTIONS":
        return response(204)
    if task_id is None:
        if method == "GET":
            return list_tasks()
        if method == "POST":
            return create_task(event)
    else:
        if method == "GET":
            return get_task(task_id)
        if method == "PUT":
            return update_task(task_id, event)
        if method == "DELETE":
            return delete_task(task_id)
    return response(405, {"message": f"Method {method} not allowed"})
