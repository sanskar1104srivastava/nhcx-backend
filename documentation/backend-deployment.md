# NHCX Backend Deployment

## Lambda Count

This backend deploys two Lambda functions from one shared container image:

1. `nhcx-bridge-dev-api` runs `nhcx.main.handler`. It serves the FastAPI app through API Gateway, including `/send`, receiver callbacks, logs, test, and sandbox helper APIs.
2. `nhcx-bridge-dev-consumer` runs `nhcx.consumer.handler`. It is triggered by `nhcxInboundQueue` and processes queued inbound callback payloads.

The shared ECR repository for the existing dev stack is:

```text
serverless-nhcx-bridge-dev
```

## Normal Code Deploy

For backend API code changes, use the code-only deployment path:

```powershell
.\scripts\deploy_nhcx_backend.ps1
```

Defaults:

```text
AWS profile: algoflow
AWS region:  ap-south-1
Stage:       dev
Functions:   api, consumer
```

The script runs local checks, builds the Docker image for `linux/amd64`, pushes it to ECR, updates both Lambdas to the same image, sets both Lambda timeouts to 300 seconds, waits for successful Lambda updates, and calls `/health`.

This path updates Lambda code and timeout only. It preserves existing Lambda environment variables, IAM, API Gateway, queues, and tables.

Useful variants:

```powershell
.\scripts\deploy_nhcx_backend.ps1 -SkipTests
.\scripts\deploy_nhcx_backend.ps1 -Function api
.\scripts\deploy_nhcx_backend.ps1 -Function consumer
.\scripts\deploy_nhcx_backend.ps1 -ImageUri "<account-id>.dkr.ecr.ap-south-1.amazonaws.com/serverless-nhcx-bridge-dev:backend-apis-YYYYMMDD-HHMM-sha"
```

## Full Stack Deploy

Use full-stack deployment only when `serverless.yml` resources or Lambda environment values change:

```powershell
.\scripts\deploy_nhcx_backend.ps1 -FullStack
```

This path requires a working Serverless Framework login/license. The normal code deploy path does not require Serverless Framework.

## Deployment Resources

The stack resources are defined in `serverless.yml`:

- API Lambda: `nhcx-bridge-dev-api`
- Consumer Lambda: `nhcx-bridge-dev-consumer`
- DynamoDB table: `nhcxRequestLog`
- SQS queue: `nhcxInboundQueue`
- SQS DLQ: `nhcxInboundDLQ`
- Large payload bucket: `nhcx-bridge-large-payloads-<account>-dev`
