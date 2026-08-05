# Taste Learnings
- Prefers incremental validation: verify each component/API works before moving on to the next step ("first check if X works, then we can move ahead"). Confidence: 0.85
- Expects live API endpoints to be tested directly (hitting the URL) during debugging, not just inspected through code review. Confidence: 0.85
- Expects thorough, exhaustive coverage: when asked to check APIs, check every use-case/workflow, not just the first few in the list ("why you only checked till pre auth, go ahead"). Confidence: 0.9
- Prefers systematic gap analysis: check docs, identify what's missing/broken across all components, then fix and add missing pieces in a deliberate iteration. Confidence: 0.85
- Requires digging into root cause when APIs fail — research documentation, check upstream API error bodies directly, and distinguish between local code bugs vs upstream/enablement issues. Confidence: 0.85
- Expects precise, documented evidence of what worked and with what parameters, not just a "works/doesn't work" summary. Confidence: 0.9
- When asked about API flows, wants the actual upstream provider's endpoint (e.g., NHCX's real API and its curl) and full request/response/callback details shown — not just the local wrapper's abstraction. Confidence: 0.8
- Prefers deploying working changes incrementally, verifying live, and updating reports — then moving on to remaining broken items. Confidence: 0.8
- When verifying API behavior, prefers calling the deployed API Gateway endpoint (not the local dev server) and gathering results/evidence via AWS — CloudWatch logs, S3 payload buckets — using read access to AWS. Confidence: 0.8
