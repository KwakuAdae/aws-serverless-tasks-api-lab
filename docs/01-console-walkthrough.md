# Console Walkthrough: Build the API by Hand

Building the API once in the AWS Console is the best way to see what SAM generates for you.
This walkthrough creates a minimal version (`GET` and `POST /tasks`) with a separate name so it
doesn't clash with the SAM stack.

## 1. Create the DynamoDB table

1. **DynamoDB → Tables → Create table**
2. Table name: `console-tasks`. Partition key: `id` (String).
3. Table settings: **Customize** → Capacity mode **On-demand**. Click **Create table**.

## 2. Create the Lambda function

1. **Lambda → Create function → Author from scratch**
2. Name: `console-tasks-handler`. Runtime: **Python 3.12**. Click **Create function**.
3. In the **Code** tab, replace `lambda_function.py` with the contents of
   [`src/app.py`](../src/app.py) and click **Deploy**.
4. **Runtime settings → Edit** → Handler: `lambda_function.lambda_handler`.
5. **Configuration → Environment variables → Edit** → add `TABLE_NAME` = `console-tasks`.
6. **Configuration → Permissions** → click the role name → **Add permissions → Create inline
   policy** → JSON:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["dynamodb:Scan", "dynamodb:GetItem", "dynamodb:PutItem",
                  "dynamodb:UpdateItem", "dynamodb:DeleteItem"],
       "Resource": "arn:aws:dynamodb:*:*:table/console-tasks"
     }]
   }
   ```

   Name it `console-tasks-dynamodb` and create it.

## 3. Create the REST API

1. **API Gateway → Create API → REST API → Build**
2. **New API**, name `console-tasks-api`, endpoint type **Regional**. Click **Create API**.

## 4. Add the `/tasks` resource and methods

1. **Create resource** → Resource name `tasks` → enable **CORS** → **Create resource**.
2. With `/tasks` selected → **Create method**:
   - Method type: **GET**
   - Integration type: **Lambda function**
   - **Lambda proxy integration: ON**
   - Lambda function: `console-tasks-handler`
   - Click **Create method** (the console adds the invoke permission for you).
3. Repeat for **POST**.

## 5. Test inside the console

Select `POST` → **Test** tab → Request body `{"title": "From the console"}` → **Test**.
You should get status `201`. Then test `GET`.

## 6. Deploy to a stage

**Deploy API** → Stage: **New stage**, name `dev` → **Deploy**. Copy the **Invoke URL**:

```bash
curl https://<api-id>.execute-api.<region>.amazonaws.com/dev/tasks
```

## 7. Require an API key with a usage plan

1. Select the `GET` method → **Method request → Edit** → **API key required: ON** → Save.
   Do the same for `POST`. **Deploy API** to `dev` again (changes aren't live until you deploy).
2. **API keys → Create API key** → name `console-key` → Auto generate → Save.
3. **Usage plans → Create usage plan** → name `console-plan`, Rate `5`, Burst `10`,
   Quota `500`/day → **Add API stage**: `console-tasks-api` / `dev` → **Add API key**: `console-key`.
4. Test:

   ```bash
   curl -i  https://<api-id>.execute-api.<region>.amazonaws.com/dev/tasks              # 403
   curl -i -H "x-api-key: <key value>" https://<api-id>.execute-api.<region>.amazonaws.com/dev/tasks   # 200
   ```

## 8. Compare with SAM

Open the SAM-deployed API (`tasks-api-lab-api`) in the console. You'll find the same resources,
methods, stage, key and usage plan, all created from about 60 lines of `template.yaml`.

## 9. Clean up the console version

Delete, in any order: the `console-tasks-api` API, the usage plan (remove its stage first),
the `console-key` API key, the `console-tasks-handler` function (and its log group
`/aws/lambda/console-tasks-handler`), its IAM role, and the `console-tasks` table.
