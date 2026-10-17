# REST API vs HTTP API vs WebSocket API

API Gateway offers three API types. This lab uses a **REST API** because it has the most
features to learn (API keys, usage plans, request validation, WAF, caching).

| | REST API | HTTP API | WebSocket API |
|---|---|---|---|
| Best for | Full-featured public/partner APIs | Simple, low-latency proxies to Lambda/HTTP | Real-time two-way apps (chat, live dashboards) |
| Price (after free tier) | ~$3.50 / million | ~$1.00 / million | $1.00 / million messages + connection minutes |
| API keys & usage plans | ✅ | ❌ | ❌ |
| Per-client throttling & quotas | ✅ | ❌ (route/stage throttling only) | ❌ |
| Request validation (models) | ✅ | ❌ | ❌ |
| Response caching | ✅ | ❌ | ❌ |
| AWS WAF | ✅ | ❌ | ❌ |
| JWT / Cognito authorizers | Cognito + Lambda authorizers | ✅ native JWT authorizer | Lambda authorizer |
| Private APIs (VPC only) | ✅ | ❌ (but private integrations ✅) | ❌ |
| Built-in CORS config | Partial (OPTIONS method) | ✅ simple setting | n/a |

## Challenge: convert this lab to an HTTP API

In `template.yaml`:

1. Change `AWS::Serverless::Api` to `AWS::Serverless::HttpApi` and remove `Auth.UsagePlan`,
   `MethodSettings` and `GatewayResponses` (not supported).
2. Replace `Cors` with `CorsConfiguration` (`AllowOrigins`, `AllowHeaders`, `AllowMethods`).
3. Change each event's `Type: Api` to `Type: HttpApi` and `RestApiId` to `ApiId`.
4. Remove the `ApiKeyId` output.
5. Update `src/app.py`: HTTP APIs send **payload format 2.0** by default, where the method is in
   `event["requestContext"]["http"]["method"]` instead of `event["httpMethod"]` (or set
   `PayloadFormatVersion: "1.0"` on the API to keep the current code).

Deploy with a new stack name and compare the latency in CloudWatch.
