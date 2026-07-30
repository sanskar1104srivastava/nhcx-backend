# Live Sandbox Tools API Check - 2026-07-29

Base bridge: configured `NHCX_BRIDGE_URL`
Participant: `1000004604@hcx`
Dummy payer: `1000003538@hcx`

Secrets and bearer tokens were not recorded.

## Local Sandbox Routes

Implemented backend routes:

- `GET /sandbox/policies`
- `POST /sandbox/dummy-payer/process`
- `POST /sandbox/dummy-payer/payment-notice`
- `POST /sandbox/status-check`
- `POST /sandbox/reject`

Frontend currently exposes only:

- policy lookup using `MobileNo`
- dummy-payer process
- dummy-payer payment notice

Frontend does not expose status-check, reject, participant list, link, or delink.

## Documentation Cross-Check

Participant Service Postman collection contains:

- `POST /participant/get/policies`
- `POST /fetch/certs`
- `POST /fetch/participants/list`
- `POST /participant/link/abha/policy`
- `POST /participant/delink/abha/policy`

Bridge wraps `get/policies`; cert fetch is exposed via `/test0/certs/self` and `/test0/certs/payer`.
Bridge does not expose participant list, link, or delink. Link/delink are mutating APIs and were not tested live.

Use-case Postman collection contains `/v1/status` and `/v1/on_status`. Official HCX docs describe status request payload as an encrypted FHIR `Task`, with `x-hcx-correlation_id` carrying the target process correlation id. Current implementation still encrypts an empty `{}` payload, so status-check is not complete.

## Live Results

### Health/Auth/Certs

- `GET /health`: HTTP 200, `{"status":"ok"}`
- `GET /test0/token`: HTTP 200, token generated
- `GET /test0/certs/self`: HTTP 200, cert found for Janani Medicare, `1000004604@hcx`
- `GET /test0/certs/payer`: HTTP 200, cert found for Dummy Payer, `1000003538@hcx`

### Policy Lookup

`GET /sandbox/policies` works for all documented identifier types:

- `MobileNo=9999999999`: HTTP 200, 3 policy rows
- `MobileNo=1234567890`: HTTP 200, 47 policy rows
- `AbhaNumber=11111111111111`: HTTP 200, 1 policy row
- `MemberId=5102411699`: HTTP 200, 1 policy row
- `AbhaNumber=12345678901234`: HTTP 200, 22 policy rows
- `MemberId=P4A86G7EM`: HTTP 200, 6 policy rows

Direct read-only participant list also works upstream:

- `PAYER`: HTTP 200, 43 rows
- `PROVIDER`: HTTP 200, 910 rows
- `TPA`: HTTP 200, 0 rows

Gap: participant list is not exposed through bridge sandbox routes.

### Dummy-Payer Process - Preauth

Fresh preauth send:

- marker: `LIVE-SANDBOX-PREAUTH-64129282`
- api_call_id: `f0aafc2d-8af8-474b-b0b0-a0f5b88be32d`
- correlation_id: `fa54c84a-6d51-4781-8a02-f85ae67fb11e`
- protocol_status: `request.queued`

Bridge sandbox tool:

- `POST /sandbox/dummy-payer/process` with `Approve/Preauth`: HTTP 502
- wrapped upstream failure: dummy payer returned HTTP 500

Direct upstream with documented camelCase body:

- `POST /dummyhcxpayer/process/request` with `correlationId`: HTTP 200, `request.dispatched`
- same request with `correlation_id`: HTTP 500

Callback after direct upstream:

- inbound apiCallId: `ca71f5a7-b7b4-4260-92c1-f3868499e104`
- useCase: `preauth`
- state: `responded_complete`
- x-hcx-status: `response.complete`

Conclusion: process/request shape is correct with `correlationId`, but deployed bridge needs retry behavior deployed.

### Dummy-Payer Process - Claim

Fresh claim send:

- marker: `LIVE-SANDBOX-CLAIM-deaad707`
- api_call_id: `adc583e1-0ab0-42fb-b928-15aa866ff01b`
- correlation_id: `e17b4ca5-556d-4bff-9bb6-69582cb4d2ac`
- protocol_status: `request.queued`

Bridge sandbox tool:

- `POST /sandbox/dummy-payer/process` with `Approve/Claim`: HTTP 502
- wrapped upstream failure: dummy payer returned HTTP 500

Direct upstream:

- `POST /dummyhcxpayer/process/request`: HTTP 200, `request.dispatched`

Callback after direct upstream:

- inbound apiCallId: `1b0ff6c7-eaa7-4fbc-8856-510dd0402d74`
- useCase: `claim`
- state: `responded_complete`
- x-hcx-status: `response.complete`

Conclusion: upstream claim process works and callback lands. Deployed bridge wrapper is still brittle.

### Payment Notice Init

Bridge sandbox tool:

- `POST /sandbox/dummy-payer/payment-notice` using claim correlation `e17b4ca5-556d-4bff-9bb6-69582cb4d2ac`: HTTP 502
- upstream validation body without provider id: `SBX-010 Provider Id Mandatory`

Direct upstream with `providerId=1000004604@hcx`:

- HTTP 200, `request.queued`
- payment notice api/correlation: `5df6b4d3-1899-4938-8bb6-6ca2f79dc4f1`

Payment notice callback:

- inbound apiCallId: `5df6b4d3-1899-4938-8bb6-6ca2f79dc4f1`
- useCase: `payment`
- state: `responded_complete`
- x-hcx-status: `request.initiated`

Conclusion: payment notice upstream works with `providerId`. Local code has the `providerId` fix, but the deployed bridge still behaves like the old wrapper.

### Status Check

Fresh coverage send:

- marker: `LIVE-SANDBOX-STATUS-COV-8c7f28cb`
- api_call_id: `23ce8f27-b319-4d2e-a2c9-0449b9eee288`
- correlation_id: `9950a832-1dff-47e5-a2ed-1601d0984ac0`
- protocol_status: `request.queued`

Bridge sandbox tool:

- `POST /sandbox/status-check`: HTTP 200
- response body fields were all null

Resulting logs:

- outbound status apiCallId: `349f25e3-b978-4d79-9290-56c5cca86754`
- status row state: `dead`
- original coverage outbound and inbound rows also marked `dead`
- errorCode: `NHCX-1012`

Conclusion: status-check route is not correct yet. It returns HTTP 200 at the wrapper level, but protocol processing fails with `NHCX-1012`. This aligns with the implementation gap: current status request payload is `{}` instead of a proper FHIR `Task`.

### Reject

Isolated fake correlation test:

- endpoint: `/communication/on_request`
- entityType: `communication`
- result: HTTP 502
- wrapped upstream failure: HCX gateway returned HTTP 500

Conclusion: reject is not proven as a generic sandbox tool. It likely needs a real in-flight inbound correlation and better gateway-error logging. It should not be treated as passing.

## Current Gaps

1. Deploy local dummy-payer fixes:
   - retry `process/request` after transient 500s
   - include `providerId` in `paymentNotice/init`

2. Rework status-check:
   - build an encrypted FHIR `Task` payload
   - use the actual target process correlation id per HCX docs
   - verify `/on_status` callback behavior without killing the original cycle

3. Expand sandbox routes if needed:
   - add read-only participant list wrapper
   - add explicit link/delink wrappers only with guardrails, because they mutate sandbox policy linkage

4. Expand frontend Sandbox Tools:
   - allow `AbhaNumber`, `MemberId`, and `MobileNo` policy lookup
   - expose participant list
   - expose status-check only after backend fix
   - hide or clearly mark reject until a safe real-correlation test path exists

## Backend Iteration - Missing APIs Added Locally

Frontend was left unchanged in this iteration.

Added backend-only sandbox routes from the local Participant Service Postman docs:

- `GET /sandbox/certs?participantId=...`
- `GET /sandbox/participants?role=PAYER|PROVIDER|TPA&fromdate=dd/MM/yyyy&todate=dd/MM/yyyy`
- `POST /sandbox/policies/link`
- `POST /sandbox/policies/delink`

The link and delink routes require `confirmSandboxMutation=true`; without that explicit flag they return HTTP 400 and do not call NHCX. This keeps the mutating sandbox policy APIs from being triggered accidentally.

Backend verification:

- `python test_smoke.py` passed
- `python -m unittest scripts.test_payer_side_samples` passed
- OpenAPI now exposes the added backend routes

Onboarding docs also list `participant/create` and full `participant/update`. Those were not added as generic sandbox tools because they mutate NHCX participant registration/cert/endpoint metadata. Existing backend code has a narrower cert-update helper, but a full create/update admin route should be added only with explicit onboarding scope and stronger guardrails.

## Deployment - Backend APIs

Deployed on 2026-07-29 to AWS profile `algoflow`, account `676373376148`, stack `nhcx-bridge-dev`.

Image:

- ECR repo: `676373376148.dkr.ecr.ap-south-1.amazonaws.com/serverless-nhcx-bridge-dev`
- Deployed tag: `backend-apis-20260729-1645`

Lambda status after deploy:

- `nhcx-bridge-dev-api`: `Active`, `LastUpdateStatus=Successful`
- `nhcx-bridge-dev-consumer`: `Active`, `LastUpdateStatus=Successful`

Serverless Framework v4 was not used for this deploy because the local metadata showed a login/license requirement. The deploy was code-only, so the existing Lambdas were updated directly to the new ECR image.

### Post-Deploy Live Checks

Read-only backend routes:

- `GET /health`: HTTP 200
- `GET /sandbox/certs?participantId=1000003538@hcx`: HTTP 200, Dummy Payer cert returned
- `GET /sandbox/participants?role=PAYER&fromdate=01/01/2026&todate=29/07/2026`: HTTP 200, 43 payer participants

Policy lookup working details:

- `identifierType=MobileNo`, `identifierValue=9999999999`: HTTP 200, 3 policy rows
- `identifierType=AbhaNumber`, `identifierValue=11111111111111`: HTTP 200, 1 policy row
- `identifierType=MemberId`, `identifierValue=5102411699`: HTTP 200, 1 policy row

The screenshot case failed because it used `identifierType=AbhaNumber` with `identifierValue=9999999999`. That value is a mobile number in sandbox, not an ABHA number. Post-deploy response for that mismatch:

- `identifierType=AbhaNumber`, `identifierValue=9999999999`: HTTP 502 wrapping NHCX `NHCX-1016`, "No policies found for given beneficiary AbhaNumber: 9999999999."

Mutation guards:

- `POST /sandbox/policies/link` without `confirmSandboxMutation=true`: HTTP 400, no upstream call
- `POST /sandbox/policies/delink` without `confirmSandboxMutation=true`: HTTP 400, no upstream call

Dummy-payer process after deploy:

- Fresh preauth marker: `LIVE-DEPLOY-PREAUTH-b02cbbef`
- preauth api_call_id: `9fd2a2a9-d570-4d2b-9500-860d7c27f5e9`
- preauth correlation_id: `fcd7cdee-5ec8-45a3-b773-13405085990c`
- `POST /sandbox/dummy-payer/process` with `Approve/Preauth`: HTTP 200, `request.dispatched`
- inbound preauth callback: `2071f514-fda4-4494-8b41-7b6c71f3f4a7`, state `responded_complete`

Claim and payment notice after deploy:

- Fresh claim marker: `LIVE-DEPLOY-CLAIM-44af9075`
- claim api_call_id: `3fc70d5e-692b-4517-a288-8e48d6b6a301`
- claim correlation_id: `58c6b6b6-3a52-4ac5-aff2-27d89da14d54`
- `POST /sandbox/dummy-payer/process` with `Approve/Claim`: HTTP 200, `request.dispatched`
- inbound claim callback: `00443eed-2139-4a2b-b4f4-6fe2f9b99caa`, state `responded_complete`
- `POST /sandbox/dummy-payer/payment-notice`: HTTP 200, `request.queued`
- payment notice correlation_id: `7ee733dc-3b69-4587-8f8f-794ae50abe52`
- inbound payment callback: `7ee733dc-3b69-4587-8f8f-794ae50abe52`, state `responded_complete`

### Predetermination Check

Local backend shape:

- sample fixture: `claimBundlePredetermination-dummyPayer.json`
- useCase: `predetermination`
- endpoint: `/predetermination/submit`
- `Claim.use`: `predetermination`
- structured `Coverage.identifier.value`: `100217`
- local `test_smoke.py` and `scripts.test_payer_side_samples` pass

Documentation cross-check:

- The sandbox use-case Postman collection includes `/v1/predetermination/submit` and `/v1/predetermination/on_submit`.
- The dummy payer PDF does not list Predetermination in its supported dummy-payer use cases.
- The dummy payer `/process/request` doc only shows `method: Preauth|Claim`, so there is no documented sandbox side-channel to trigger a predetermination callback after submit.

Live submit:

- marker: `LIVE-PREDET-404e2515`
- api_call_id: `f5338251-3d85-493a-9aa2-b35109fc5da0`
- correlation_id: `84d40785-8e40-44cd-9b1f-913d5cbdd384`
- gateway endpoint: `https://apisbx.abdm.gov.in/hcx/v1/predetermination/submit`
- result: HTTP 400 from NHCX, stored locally as outbound `error`
- NHCX error: `NHCX-1002`, "Sender not registered in NHCX. Please register in NHCX portal and try again."

Registry cross-check:

- `GET /sandbox/participants?role=PROVIDER&fromdate=01/01/2026&todate=29/07/2026` returns Janani Medicare as `1000004604@hcx`

Conclusion: the participant exists globally and preauth works, but the sandbox gateway rejects this participant for the `predetermination` entity. This is not a local bundle validation failure. It needs NHCX sandbox participant/use-case enablement for predetermination, or NHCX confirmation that the provider should not test predetermination separately in this sandbox lane.

Backend response handling update:

- `POST /send` now surfaces outbound failures as HTTP 502 with the upstream NHCX error detail instead of a generic HTTP 500.
- Added smoke coverage for this behavior.

## Gap Pass - 2026-07-30

Scope: backend only, excluding the predetermination enablement blocker above.

Documented API comparison:

- The sandbox use-case Postman collection includes Search: `/v1/search/submit` and `/v1/search/on_submit`.
- Search was missing from backend `UseCase`, `OutboundEndpoint`, and receiver route coverage.
- Added local backend support for `UseCase.SEARCH`, `OutboundEndpoint.SEARCH`, and `/search/on_submit` plus `/v1/search/on_submit`.
- No Search sample fixture exists in this repo, so Search is route/API-shape support only until a real TaskBundle search fixture/request is added.

Live checks:

- Insurance plan:
  - marker: `LIVE-GAP-INSURANCEPLAN-ccdd7449`
  - outbound api_call_id: `2a03bcdc-43bd-4578-b6aa-120673b04454`
  - correlation_id: `c115ebdd-e36a-480d-bde2-85248a9e59e3`
  - send: HTTP 200, `request.queued`
  - callback: inbound `717e2176-0c5d-4ba5-9d8d-604b3cfece18`, state `responded_complete`

- Coverage eligibility:
  - marker: `LIVE-GAP-COVERAGEELIGIBILITY-d9f1012d`
  - outbound api_call_id: `9dce698c-7573-4151-ad18-74d00220aad1`
  - correlation_id: `d4f6dbed-5c22-4258-a0ae-fca6fed212ac`
  - send: HTTP 200, `request.queued`
  - callback: inbound `769e955c-53ad-4798-9944-36388f85e51d`, state `responded_complete`

- Task/reprocess:
  - marker: `LIVE-GAP-TASK-ea8d754c`
  - outbound api_call_id: `fa6317d0-b4e7-4253-a921-895b2286145d`
  - correlation_id: `50b3362a-43cb-4c7f-a95b-96df8237554d`
  - send: HTTP 200, `request.queued`
  - no inbound task callback observed in repeated log polls after roughly two minutes
  - docs list `/v1/task/submit` and `/v1/task/on_submit`, but dummy payer implementation docs do not list reprocess/task as a supported dummy-payer test use case

- Status check:
  - target coverage correlation_id: `d4f6dbed-5c22-4258-a0ae-fca6fed212ac`
  - wrapper returned HTTP 200 with empty/null protocol fields
  - local status row `6035c58f-5729-45d9-9e56-406c6b6fbda2` became `dead`
  - this reconfirms `/sandbox/status-check` is not healthy; it still needs the documented encrypted status payload/request shape

- Communication:
  - seed preauth marker: `LIVE-GAP-COMM-PREAUTH-fa848562`
  - preauth api_call_id: `cbc7c2fb-7e51-47e9-8065-02f4a4976481`
  - preauth correlation_id: `65211f56-dfa7-401b-bca9-38a4ac811d8e`
  - immediate bridge `/sandbox/dummy-payer/process` with `Query/Preauth`: HTTP 502 wrapping upstream HTTP 400
  - direct retry later with the same `Query/Preauth` body: HTTP 200, `request.dispatched`
  - direct `Query/Claim` check returned upstream `SBX-005`, "Request Action was not matching..."
  - no inbound communication callback was observed in repeated log polls

Local backend fixes from this pass:

- Added Search enum/callback-route support.
- Improved dummy-payer sandbox error handling so upstream response bodies such as `SBX-005` are preserved in backend errors.
- Smoke tests now cover Search callback route registration and dummy-payer upstream body preservation.

Still not deployed as working:

- `/sandbox/status-check`: still requires a proper encrypted FHIR `Task` implementation before treating it as healthy.
- `/sandbox/reject`: still not proven as a generic tool; should be tested only with a real in-flight inbound correlation.
- Full onboarding `participant/create` and broad `participant/update`: intentionally not exposed as generic sandbox APIs.
- Predetermination submit: backend payload/route is wired, but live NHCX sandbox rejects the participant with `NHCX-1002` for `/predetermination/submit`.
- Search: local route/enum support added, but no repo fixture or live Search request has been proven.
- Task/reprocess: outbound is accepted by NHCX, but dummy-payer callback was not observed.
- Communication: immediate Query trigger through the bridge is timing-sensitive/broken as a one-click flow, and no communication callback was observed after a later direct `request.dispatched`.

## Backend Final Iteration - 2026-07-30

Scope: backend only. Frontend was left unchanged.

Documentation used:

- Sandbox use-case Postman collection: `/v1/search/submit`, `/v1/search/on_submit`, `/v1/task/submit`, `/v1/task/on_submit`, `/v1/status`, `/v1/on_status`.
- `NHCX-Services-Request and Response-Updated.xlsx`: Status says `/v1/status` `x-hcx-correlation_id` should be the API caller ID of the request that needs a status check.
- Official HCX supporting API docs: Status request payload is FHIR `Task`; status can be returned synchronously by HCX and may be forwarded to the recipient for `/hcx/on_status`.
- Dummy payer implementation PDF: dummy-payer side-channel support is documented for Insurance Plan, Coverage Eligibility, Preauth, Claim, Payment Notice, and Communication; it does not list Predetermination, Search, or Task/Reprocess.

Backend changes deployed:

- Added Search backend support: `UseCase.SEARCH`, `OutboundEndpoint.SEARCH`, `/search/on_submit`, `/v1/search/on_submit`, sample fixture, and payer-side script mapping.
- Corrected Task/Reprocess fixture claim number to `7612345`, matching the successful dummy-payer claim callback evidence.
- Reworked Status Check to send an encrypted FHIR `Task` payload and use the sandbox-required original `api_call_id` as the status transport correlation.
- Changed new primary outbound cycles to default `correlation_id = api_call_id`. Explicit correlation IDs are still preserved for related/reply flows.
- Improved dummy-payer sandbox tools: upstream error bodies are preserved, `Query/Preauth` transient 400 readiness is retried, and payment notice init includes `providerId`.
- `POST /send` returns HTTP 502 with upstream details on NHCX failures instead of hiding them behind a generic 500.

Final deployment:

- Image tag: `backend-gapfix-20260730-1308`
- Image digest / Lambda `CodeSha256`: `06d2735c673fd88e3cf3fd1a342ba1555c93119c98d12946bb036d44652d1804`
- `nhcx-bridge-dev-api`: `Active`, `LastUpdateStatus=Successful`, timeout `30`
- `nhcx-bridge-dev-consumer`: `Active`, `LastUpdateStatus=Successful`, timeout `6`

Verification:

- `python test_smoke.py`: passed
- `python -m unittest scripts.test_payer_side_samples`: passed
- `python -m compileall nhcx scripts test_smoke.py`: passed
- `GET /health`: HTTP 200, `{"status":"ok"}`

Live API outcomes:

- Coverage eligibility after final ID fix:
  - marker: `LIVE-FIX6-CORRSTATUS-fe04def3`
  - api_call_id: `05402263-34dd-4340-b75b-d281a1c5e877`
  - correlation_id: `05402263-34dd-4340-b75b-d281a1c5e877`
  - IDs matched: true
  - send: HTTP 200, `request.queued`
  - callback: inbound `aee7f613-9ff4-466f-9638-41c3fd1d49bf`, state `responded_complete`

- Search:
  - marker: `LIVE-FIX-SEARCH-979059ce`
  - api_call_id: `00b14b0b-771d-4454-bc48-006141e97c58`
  - route reached NHCX `/v1/search/submit`
  - live result: NHCX HTTP 400, bridge HTTP 502
  - NHCX error: `NHCX-1002`, "Sender not registered in NHCX. Please register in NHCX portal and try again."
  - conclusion: backend route/sample exists; live blocker is participant/use-case enablement for Search.

- Task/Reprocess:
  - marker: `LIVE-FIX-TASK-d6079067`
  - api_call_id: `b5521b2d-e2dc-47e0-9a6c-c680df5679cb`
  - correlation_id: `733805f0-9715-4709-8ebb-b0d30ae946d5`
  - send: HTTP 200, `request.queued`
  - no inbound task callback observed
  - conclusion: NHCX accepts outbound Task/Reprocess, but dummy payer does not appear to support the callback in this sandbox path.

- Status Check:
  - target coverage api/correlation: `05402263-34dd-4340-b75b-d281a1c5e877`
  - status api_call_id: `8c98a81a-732c-4d5e-8a51-a26091d745b0`
  - request shape: encrypted FHIR `Task`, `Task.code=status`, status correlation set to original `api_call_id`
  - live result: NHCX HTTP 400, bridge HTTP 502
  - NHCX error: `NHCX-1012`, "No records found with the requested api caller id. Please try again with a valid api caller id."
  - normal coverage callback still arrived after the status failure
  - conclusion: backend request shape and ID defaults are fixed, but the NHCX sandbox still cannot status-check even a fresh dummy-payer coverage request. Treat as NHCX/sandbox support blocker pending confirmation from NHCX.

- Communication:
  - seed preauth marker: `LIVE-FIX-COMM-PREAUTH-39b468b5`
  - preauth api_call_id: `fcf640ca-bc65-492c-81a0-04ce44e6f785`
  - preauth correlation_id: `69a36457-d9d9-4edc-9d1a-c1dcaa297e96`
  - bridge `/sandbox/dummy-payer/process` with `Query/Preauth`: HTTP 200 after retry, `request.dispatched`
  - no inbound communication callback observed
  - conclusion: backend wrapper timing issue is fixed; dummy-payer communication callback remains unproven.

Current backend status:

- Working/proven: policy lookup, participant list/certs, insurance plan, coverage eligibility, preauth, claim, payment notice, dummy-payer approve flows, guarded link/delink wrappers.
- Implemented but upstream-blocked: predetermination (`NHCX-1002`), search (`NHCX-1002`), status (`NHCX-1012`).
- Implemented but callback not proven: task/reprocess, communication.
- Not treated as generic working tool: `/sandbox/reject`; needs a real in-flight inbound correlation test.
