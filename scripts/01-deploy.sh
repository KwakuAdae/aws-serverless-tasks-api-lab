#!/usr/bin/env bash
# Step 1: Build and deploy the API with AWS SAM, then print the URL and API key.
set -euo pipefail
source "$(dirname "$0")/config.sh"
cd "$(dirname "$0")/.."

echo ">> Building..."
sam build

echo ">> Deploying stack '${STACK_NAME}' to ${AWS_REGION}..."
sam deploy --stack-name "$STACK_NAME" --region "$AWS_REGION" --no-fail-on-empty-changeset

API_URL=$(stack_output ApiUrl)
API_KEY_ID=$(stack_output ApiKeyId)
API_KEY=$(aws apigateway get-api-key --api-key "$API_KEY_ID" --include-value \
  --query value --output text --region "$AWS_REGION")

# Config for the browser demo (git-ignored, so your key is never committed)
cat > frontend/config.js <<JS
window.API_URL = "${API_URL}";
window.API_KEY = "${API_KEY}";
JS

echo ""
echo "✅ API deployed"
echo "   export API_URL=${API_URL}"
echo "   export API_KEY=${API_KEY}"
