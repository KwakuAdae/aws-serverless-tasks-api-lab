#!/usr/bin/env bash
# Step 2: Exercise every route of the deployed API with curl.
set -euo pipefail
source "$(dirname "$0")/config.sh"

API_URL="${API_URL:-$(stack_output ApiUrl)}"
API_KEY="${API_KEY:-$(aws apigateway get-api-key --api-key "$(stack_output ApiKeyId)" \
  --include-value --query value --output text --region "$AWS_REGION")}"
H=(-H "x-api-key: ${API_KEY}" -H "Content-Type: application/json")

step() { echo ""; echo "── $*"; }

step "Request WITHOUT an API key (expect 403 Forbidden)"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "${API_URL}/tasks"

step "POST /tasks (create)"
TASK=$(curl -s "${H[@]}" -X POST "${API_URL}/tasks" -d '{"title":"Learn API Gateway"}')
echo "$TASK"
ID=$(echo "$TASK" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

step "GET /tasks (list)"
curl -s "${H[@]}" "${API_URL}/tasks"; echo

step "GET /tasks/${ID}"
curl -s "${H[@]}" "${API_URL}/tasks/${ID}"; echo

step "PUT /tasks/${ID} (mark done)"
curl -s "${H[@]}" -X PUT "${API_URL}/tasks/${ID}" -d '{"done":true}'; echo

step "POST /tasks with invalid body (expect 400)"
curl -s "${H[@]}" -X POST "${API_URL}/tasks" -d '{"title":""}' -w "  HTTP %{http_code}\n"

step "DELETE /tasks/${ID} (expect 204)"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "${H[@]}" -X DELETE "${API_URL}/tasks/${ID}"

step "GET deleted task (expect 404)"
curl -s "${H[@]}" "${API_URL}/tasks/${ID}" -w "  HTTP %{http_code}\n"

echo ""
echo "✅ All routes exercised."
