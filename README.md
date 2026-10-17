# Lab: Build a Serverless REST API with Amazon API Gateway

A hands-on lab that builds a **Tasks REST API** with **Amazon API Gateway**, **AWS Lambda**
(Python) and **Amazon DynamoDB**. It's deployed as Infrastructure as Code with **AWS SAM**, and
secured with an **API key, usage plan and throttling**. A small web page calls the API from
the browser using CORS.

```
                      ┌──────────────────────── Amazon API Gateway (REST API, stage: dev) ───────────────────┐
 ┌──────────────┐     │  ① API key check (x-api-key)   ② Usage plan: 10 req/s, burst 20, 1000/day            │
 │ curl /       │ ──▶ │  ③ Routes:  GET /tasks · POST /tasks · GET|PUT|DELETE /tasks/{id}  ④ CORS            │
 │ web page     │ ◀── │  ⑤ Lambda proxy integration                                                           │
 └──────────────┘     └──────────────────────────────────┬────────────────────────────────────────────────────┘
                                                         ▼
                                    ┌──────────────────────────────┐        ┌────────────────────────┐
                                    │ AWS Lambda (Python 3.12)     │ ─────▶ │ Amazon DynamoDB        │
                                    │ src/app.py: routing,         │        │ table: tasks           │
                                    │ validation, JSON responses   │        │ (on-demand)            │
                                    └──────────────┬───────────────┘        └────────────────────────┘
                                                   ▼
                                    CloudWatch Logs · X-Ray tracing · 5XX alarm
```

## What you will learn

- What API Gateway does: **resources, methods, integrations, stages and deployments**
- **Lambda proxy integration** and the event/response format it uses
- Building a CRUD API backed by DynamoDB with **least-privilege IAM**
- Defining everything as code with **AWS SAM** (a CloudFormation extension)
- Protecting an API with **API keys, usage plans, throttling and quotas**
- **CORS**, so a browser app on another origin can call your API
- Testing locally (unit tests + `sam local`) and observing with **CloudWatch** and **X-Ray**

## API reference

All requests need the header `x-api-key: <your key>`.

| Method | Path | Body | Success | Errors |
|--------|------|------|---------|--------|
| GET | `/tasks` | — | `200` list of tasks | |
| POST | `/tasks` | `{"title": "Buy milk", "done": false}` | `201` created task | `400` invalid body |
| GET | `/tasks/{id}` | — | `200` task | `404` |
| PUT | `/tasks/{id}` | `{"title"?: "...", "done"?: true}` | `200` updated task | `400`, `404` |
| DELETE | `/tasks/{id}` | — | `204` no content | `404` |

API Gateway itself returns `403` for a missing or invalid API key and `429` when throttled.

A task looks like:

```json
{ "id": "5f0c…", "title": "Learn API Gateway", "done": false,
  "createdAt": "2026-10-15T20:00:00.123456+00:00", "updatedAt": "2026-10-15T20:00:00.123456+00:00" }
```

## Project structure

```
aws-serverless-tasks-api-lab/
├── template.yaml          # SAM template: API Gateway, Lambda, DynamoDB, API key, usage plan, alarm
├── samconfig.toml         # default deploy settings (stack name, region)
├── src/
│   └── app.py             # Lambda handler: routing, validation, DynamoDB calls
├── tests/
│   ├── test_app.py        # 15 unit tests using moto (no AWS needed)
│   └── requirements.txt
├── events/                # sample API Gateway events for `sam local invoke`
├── frontend/
│   └── index.html         # browser demo that calls the API
├── scripts/
│   ├── config.sh
│   ├── 01-deploy.sh       # sam build + deploy, prints URL and API key
│   ├── 02-test-api.sh     # exercises every route with curl
│   ├── 03-throttle-test.sh# shows HTTP 429 throttling
│   └── 04-cleanup.sh      # deletes the stack
└── docs/
    ├── 01-console-walkthrough.md   # build the same API by clicking in the console
    ├── 02-troubleshooting.md
    └── 03-rest-vs-http-api.md
```

## Prerequisites

| Tool | Check | Install |
|------|-------|---------|
| AWS account | — | Everything here fits in the **free tier** |
| AWS CLI v2 | `aws --version` | then `aws configure` |
| AWS SAM CLI | `sam --version` | `brew install aws-sam-cli` or [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) |
| Python 3.12+ | `python3 --version` | for unit tests |
| Docker *(optional)* | `docker --version` | only for `sam local` |

---

## Quick start (automated)

```bash
git clone https://github.com/KwakuAdae/aws-serverless-tasks-api-lab.git
cd aws-serverless-tasks-api-lab

./scripts/01-deploy.sh          # build & deploy (~2 min), prints API_URL and API_KEY
./scripts/02-test-api.sh        # call every route
./scripts/03-throttle-test.sh   # see throttling (HTTP 429)
open frontend/index.html        # try the web page
./scripts/04-cleanup.sh         # delete everything
```

The rest of this guide walks through each step and explains what's happening. To build the
API by hand in the console first (great for understanding the moving parts), see
[docs/01-console-walkthrough.md](docs/01-console-walkthrough.md).

---

## Step 1: Understand API Gateway's building blocks

| Concept | In this lab |
|---------|-------------|
| **REST API** | `tasks-api-lab-api`, the container for everything below |
| **Resource** | A URL path: `/tasks` and `/tasks/{id}` (`{id}` is a *path parameter*) |
| **Method** | An HTTP verb on a resource: `GET /tasks`, `POST /tasks`, … |
| **Integration** | What a method calls. Here it's **Lambda proxy**: the whole request goes to Lambda as JSON and Lambda returns the full HTTP response |
| **Deployment & Stage** | A snapshot of the API published at a URL. Stage `dev` → `https://{api-id}.execute-api.{region}.amazonaws.com/dev` |
| **API key & Usage plan** | Identifies callers and enforces rate limits and quotas per key |

## Step 2: Read the Lambda function

Open [`src/app.py`](src/app.py). With **proxy integration**, API Gateway sends Lambda an event like:

```json
{
  "httpMethod": "PUT",
  "path": "/tasks/5f0c…",
  "pathParameters": { "id": "5f0c…" },
  "headers": { "x-api-key": "…", "Content-Type": "application/json" },
  "body": "{\"done\": true}",
  "requestContext": { "requestId": "…", "stage": "dev", "identity": { "sourceIp": "…" } }
}
```

and expects a response shaped like:

```json
{ "statusCode": 200, "headers": { "Content-Type": "application/json" }, "body": "{…}" }
```

The handler routes on `httpMethod` + `pathParameters.id`, validates the JSON body, talks to
DynamoDB with `boto3`, and returns proper status codes (`201`, `204`, `400`, `404`, `405`).
`body` must be a **string**: forgetting `json.dumps` is the #1 cause of `502` errors.

## Step 3: Run the unit tests (no AWS needed)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r tests/requirements.txt
pytest -v
```

[moto](https://github.com/getmoto/moto) fakes DynamoDB in memory, so the tests cover create,
list, get, update, delete, validation errors, 404s, CORS preflight and unsupported methods.

```
15 passed in 1.9s
```

## Step 4: Read the SAM template

[`template.yaml`](template.yaml) is the whole stack as code. Highlights:

```yaml
TasksApi:
  Type: AWS::Serverless::Api
  Properties:
    StageName: dev
    Cors: { AllowOrigin: "'*'", AllowHeaders: "'Content-Type,x-api-key'", ... }
    Auth:
      ApiKeyRequired: true            # every method requires x-api-key
      UsagePlan:
        CreateUsagePlan: PER_API
        Throttle: { RateLimit: 10, BurstLimit: 20 }
        Quota:    { Limit: 1000, Period: DAY }
```

- Each `Events:` entry on `TasksFunction` creates a **resource + method + Lambda proxy
  integration**, plus the permission for API Gateway to invoke the function.
- `DynamoDBCrudPolicy` grants the function access to **only** the tasks table.
- `GatewayResponses` adds CORS headers to API Gateway's own errors (403/429), so the browser
  can read them.
- `Api5xxAlarm` is a CloudWatch alarm that fires if the API returns server errors.

## Step 5: (Optional) Test locally with SAM

Requires Docker. Invoking the function locally still uses the **real** DynamoDB table, so deploy first
(Step 6) or expect a "table not found" error:

```bash
sam build
sam local invoke TasksFunction -e events/list-tasks.json \
  --env-vars <(echo '{"TasksFunction":{"TABLE_NAME":"tasks-api-lab-tasks"}}')
```

## Step 6: Deploy

```bash
sam build
sam deploy            # uses samconfig.toml: stack tasks-api-lab in us-east-1
```

Or use `sam deploy --guided` to be asked for each setting. SAM packages the code, uploads it to
an S3 bucket it manages, and creates a CloudFormation stack. When it finishes you'll see:

```
Outputs
Key       ApiUrl
Value     https://abc123.execute-api.us-east-1.amazonaws.com/dev
Key       ApiKeyId
Value     xyz789
```

Get the **API key value** (the output shows only its ID):

```bash
export API_URL=$(aws cloudformation describe-stacks --stack-name tasks-api-lab \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
export API_KEY=$(aws apigateway get-api-key --include-value --query value --output text \
  --api-key $(aws cloudformation describe-stacks --stack-name tasks-api-lab \
  --query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" --output text))
```

(`./scripts/01-deploy.sh` does all of this for you.)

## Step 7: Call the API

```bash
# No key → API Gateway rejects the request before Lambda runs
curl -i $API_URL/tasks                                    # HTTP/2 403 {"message":"Forbidden"}

# Create
curl -s -X POST $API_URL/tasks -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" -d '{"title":"Learn API Gateway"}'

# List
curl -s $API_URL/tasks -H "x-api-key: $API_KEY"

# Update (use an id from the list)
curl -s -X PUT $API_URL/tasks/<id> -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" -d '{"done":true}'

# Delete
curl -i -X DELETE $API_URL/tasks/<id> -H "x-api-key: $API_KEY"   # HTTP/2 204
```

Or run everything at once: `./scripts/02-test-api.sh`.

✅ **Checkpoint:** open **DynamoDB → Tables → tasks-api-lab-tasks → Explore items** and see your tasks.

## Step 8: Throttling and quotas

```bash
./scripts/03-throttle-test.sh 60
#   38 200
#   22 429
```

The usage plan allows 10 requests/second with a burst of 20. Extra requests get
**`429 Too Many Requests`** from API Gateway, and your Lambda isn't even invoked, which protects
your backend and your bill. See the plan under **API Gateway → Usage plans**.

## Step 9: Call the API from a browser (CORS)

`01-deploy.sh` writes `frontend/config.js` with your URL and key (it's git-ignored). Open the page:

```bash
open frontend/index.html          # macOS (Linux: xdg-open, Windows: start)
```

Add, tick and delete tasks. Open DevTools → Network to see the **preflight `OPTIONS`** request
the browser sends before `POST`/`PUT`/`DELETE`, and the `Access-Control-Allow-*` headers in
the responses.

> ⚠️ An API key in browser code is visible to anyone. API keys are for **identifying and
> throttling** clients, not for authentication. For real user auth use **Amazon Cognito** or a
> **Lambda authorizer** (see *Going further*).

## Step 10: Observe

```bash
sam logs --stack-name tasks-api-lab --tail          # Lambda logs
```

- **CloudWatch → Metrics → ApiGateway**: `Count`, `Latency`, `IntegrationLatency`, `4XXError`, `5XXError`
- **X-Ray → Traces**: tracing is on, so you can see time spent in API Gateway → Lambda → DynamoDB
- **CloudWatch → Alarms**: `tasks-api-lab-api-5xx`

## Step 11: Change and redeploy

Edit `src/app.py` (for example, reject titles shorter than 3 characters), add a test, run
`pytest`, then:

```bash
sam build && sam deploy
```

SAM creates a new **deployment** of the `dev` stage automatically. To experiment with a
second stage: `sam deploy --stack-name tasks-api-prod --parameter-overrides StageName=prod`.

## Step 12: Clean up

```bash
./scripts/04-cleanup.sh            # = sam delete --stack-name tasks-api-lab
```

This deletes the API, stage, API key, usage plan, Lambda, DynamoDB table (and its data), log
group and alarm.

---

## Cost

Everything used here is covered by the AWS free tier for normal lab usage (API Gateway: 1M REST
calls/month for 12 months; Lambda: 1M requests/month; DynamoDB on-demand: pennies). Beyond the
free tier, REST API calls cost ~$3.50 per million.

## Going further

- **Authentication**: add a Cognito user pool authorizer or a Lambda (JWT) authorizer
- **Request validation**: add an OpenAPI model so API Gateway rejects bad bodies before Lambda
- **Custom domain**: `api.yourdomain.com` with an ACM certificate and Route 53
- **WAF**: attach AWS WAF to block abusive IPs and common attacks
- **HTTP API**: rebuild this as a cheaper, faster HTTP API, see [docs/03-rest-vs-http-api.md](docs/03-rest-vs-http-api.md)
- **CI/CD**: run `pytest` and `sam deploy` from GitHub Actions
- Sister labs: [ECS Fargate](https://github.com/KwakuAdae/aws-ecs-fargate-website-lab) ·
  [EKS](https://github.com/KwakuAdae/aws-eks-website-lab)

## Troubleshooting

See [docs/02-troubleshooting.md](docs/02-troubleshooting.md).

## Author

**Kwaku Adae**: [github.com/KwakuAdae](https://github.com/KwakuAdae)

Feedback and reviews are welcome. Open an issue or a pull request!
