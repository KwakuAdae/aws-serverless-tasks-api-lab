#!/usr/bin/env bash
# Step 3: Fire a burst of requests to see the usage plan throttle kick in (HTTP 429).
set -euo pipefail
source "$(dirname "$0")/config.sh"

API_URL="${API_URL:-$(stack_output ApiUrl)}"
API_KEY="${API_KEY:-$(aws apigateway get-api-key --api-key "$(stack_output ApiKeyId)" \
  --include-value --query value --output text --region "$AWS_REGION")}"
COUNT="${1:-60}"

echo ">> Sending ${COUNT} parallel requests (usage plan: 10 req/s, burst 20)..."
seq "$COUNT" | xargs -P 30 -I{} curl -s -o /dev/null -w "%{http_code}\n" \
  -H "x-api-key: ${API_KEY}" "${API_URL}/tasks" | sort | uniq -c
echo "   200 = allowed, 429 = Too Many Requests (throttled by API Gateway)"
