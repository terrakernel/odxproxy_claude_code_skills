# ODXProxy Error Catalog

Authoritative source: https://odxproxy.io/docs/errors . All `/api/*` responses
use the JSON-RPC 2.0 envelope with mutually exclusive `result` / `error`.

## Error object

```json
{ "error": { "code": <number>, "message": "<string>", "data": <optional> } }
```

## Codes

| HTTP | JSON-RPC code | Trigger | Client handling |
|------|---------------|---------|-----------------|
| 200 | *(Odoo's own)* | Odoo logic / validation / permission error | Surface `message`/`data` to the user; this is a business error, not a transport failure. Do **not** retry blindly. |
| 400 | `-32001` | `action` not in the allowlist | Bug in the client — fix the action value. |
| 400 | `-32002` | `call_method` missing `fn_name` | Provide a non-empty `fn_name`. |
| 401 | `-32000` | Invalid / missing `x-api-key` | Fix the **proxy** api key (header), not the Odoo key. |
| 403 | `0` | Expired / invalid proxy license | Operational — renew the proxy license; not fixable client-side. |
| 502 | `-32004` | Proxy cannot reach Odoo | Transport — check Odoo connectivity; safe to retry with backoff. |
| 504 | `-32003` | Odoo call timed out | Retry with backoff and/or raise `x-request-timeout`. |
| 500 | `-32005` | Proxy failed to decode Odoo's response | Investigate proxy logs; not retryable by the client. |

## Handling strategy

- **Retryable:** `-32004` (502), `-32003` (504) → exponential backoff, bounded.
- **Fix-the-request:** `-32001`, `-32002` → programming errors, fail fast.
- **Fix-the-config:** `-32000` (proxy key), `0` (license) → surface clearly; no
  retry.
- **Business errors (200 + error):** Odoo's own codes/messages — show the
  message to the user; the same call will keep failing until inputs change.
- **`-32005` (500):** proxy-side; log `request_id` and escalate.

Always log the response `id` / `request_id` — it ties client logs to proxy logs.

## How SDKs surface these

Official SDKs map codes to typed exceptions while preserving the original
`code`, `message`, `data`, `http_status`, and `request_id` — but the **class
names differ per SDK**. JS/TS: `AuthError`, `OdooLogicError`,
`OdooTimeoutError`, base `OdxError`. .NET: `OdxAuthException`,
`OdxOdooException`, `OdxUpstreamTimeoutException`, base `OdxException` (with
`Status`, `RpcCode`, `RpcData`). Swift: a single enum `OdxProxyError` with a
case per code. Python/Java/PHP collapse everything into one exception type.
See `sdks.md` before catching anything by name.
