# Troubleshooting

Useful first checks:

```bash
sam logs --stack-name tasks-api-lab --tail             # Lambda logs and errors
curl -i -H "x-api-key: $API_KEY" $API_URL/tasks        # -i shows status and headers
```

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `403 {"message":"Forbidden"}` | Missing or wrong `x-api-key` header, or the key isn't attached to a usage plan for this stage | Re-read the key: `aws apigateway get-api-key --api-key <id> --include-value`. Check **Usage plans → API keys** |
| `403 {"message":"Missing Authentication Token"}` | Wrong path or method (API Gateway returns this for routes that don't exist) | Check the URL includes the stage: `…/dev/tasks`, not `…/tasks` |
| `429 Too Many Requests` | Usage plan throttle or daily quota hit | Wait a second (rate) or until tomorrow (quota), or raise limits in `template.yaml` |
| `502 Bad Gateway` / `Internal server error` | Lambda crashed or returned a malformed response (e.g. `body` not a string) | `sam logs …` shows the traceback. Proxy responses need `statusCode` and a **string** `body` |
| `500` with `AccessDeniedException` in logs | Lambda role can't access the table | Make sure the function has `DynamoDBCrudPolicy` for the right table |
| `ResourceNotFoundException` in logs | `TABLE_NAME` points at a table that doesn't exist (common with `sam local`) | Pass the deployed table name via `--env-vars` |
| Browser: `blocked by CORS policy` | Response is missing `Access-Control-Allow-Origin`, or the preflight failed | Lambda adds CORS headers on every response, and `GatewayResponses` covers 4XX/5XX. Redeploy after changing CORS. Check `AllowedOrigin` |
| Web page says "Missing config.js" | `frontend/config.js` not generated | Run `./scripts/01-deploy.sh` (it writes the file) |
| `sam deploy`: `Requires capabilities: [CAPABILITY_IAM]` | IAM roles are created by the stack | Already set in `samconfig.toml`; when deploying manually add `--capabilities CAPABILITY_IAM` |
| `sam deploy`: `S3 Bucket not specified` | No artifact bucket | `resolve_s3 = true` is in `samconfig.toml`, or use `sam deploy --guided` |
| Stack stuck in `ROLLBACK_COMPLETE` | A previous deploy failed | `sam delete --stack-name tasks-api-lab`, fix the error from the CloudFormation **Events** tab, deploy again |
| Changes in the console aren't live | REST API changes need a new deployment | **Deploy API** to the stage (SAM does this automatically) |
