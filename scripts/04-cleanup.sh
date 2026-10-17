#!/usr/bin/env bash
# Step 4: Delete the stack (API, Lambda, DynamoDB table, API key, usage plan, alarm).
set -euo pipefail
source "$(dirname "$0")/config.sh"

echo ">> Deleting stack '${STACK_NAME}'..."
sam delete --stack-name "$STACK_NAME" --region "$AWS_REGION" --no-prompts
rm -f "$(dirname "$0")/../frontend/config.js"
echo "✅ Cleanup complete."
