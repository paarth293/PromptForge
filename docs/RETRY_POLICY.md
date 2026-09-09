# PromptForge — Error & Retry Policy Conventions

This document records the error handling and retry policies across PromptForge services (Phase 0, Step 7).

---

## 1. Standard Error Envelope
All API endpoints return an envelope on error:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR | POLICY_VIOLATION | LLM_EXECUTION_ERROR | ...",
    "message": "Human-readable description",
    "details": {}
  },
  "request_id": "uuid-v4"
}
```

## 2. LLM Transient Failure Policy
When an upstream LLM call encounters:
* HTTP 429 (Rate Limit Exceeded)
* HTTP 500 / 502 / 503 (Provider Server Error)
* Network / Read Timeouts

**Action:**
1. Exponential backoff with jitter: $t = \min(t_{\text{initial}} \times 2^{\text{attempt}} + \text{jitter}, t_{\text{max}})$
2. Initial delay: $1.0\text{s}$, Max delay: $8.0\text{s}$, Max attempts: 3.
3. If all attempts fail, gracefully fall back to the secondary diverse model provider or designated mock fallback.

## 3. JSON Output Validation & Self-Correction Policy
For prompt chains requiring structured JSON output:
1. Parse output as JSON.
2. Validate against the target Pydantic model.
3. If malformed or schema mismatch occurs:
   * Re-prompt the model once with the exact validation error diagnostic appended.
   * Maximum re-prompt attempts: 2.
   * If failure persists, raise `ValidationException`.
