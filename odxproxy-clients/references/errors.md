# ODXProxy Error Catalog

Authoritative source: https://odxproxy.io/docs/errors and the proxy repo's
`SYSTEM_ARCHITECTURE.md` §6 and §7.1. All `/api/*`, `/v1/*` and `/v2/*`
responses use the JSON-RPC 2.0 envelope with mutually exclusive
`result` / `error`.

## Error object

```json
{ "error": { "code": <number>, "message": "<string>", "data": <optional> } }
```

**Codes `100`–`599` are Odoo HTTP statuses; `0` and negative codes are the
proxy's.** A client can rely on that split.

## Codes

| HTTP | JSON-RPC code | API | Trigger | Client handling | Retry? |
|------|---------------|-----|---------|-----------------|--------|
| 200 | *Odoo's own*: `200` on Odoo ≤18, `0` on 19+ (message `Odoo Server Error`) | v1 | Odoo logic / validation / permission error | Business error — the real text is `data.message`; branch on `data.name` | no |
| 200 | `401` | v2 (v1 rarely) | **Odoo** rejected its API key: invalid, expired, wrong scope, or a password | Not the proxy key. Usually an expired non-admin key — tell the end user to issue a new one | no |
| 200 | `403` | v2 | Access rights, or a private (`_`-prefixed) method | Surface | no |
| 200 | `404` | v2 | Unknown model/method, or record does not exist | Fix model/method name or ids | no |
| 200 | `409` | v2 | Odoo lock conflict | Retry | **yes**, with backoff |
| 200 | `422` | v2 | Validation/user error, or bad arguments (unknown kwarg, `ids` on an `@api.model` method) | Surface; fix the request if it's an argument error | no |
| 200 | `500`, other 5xx | v2 | Odoo server error | Surface / log | no |
| 200 | `-32006` | v2 | Odoo answered a non-JSON 404: no JSON-2 (Odoo ≤18 → use v1), or the database is wrong / not selectable on that host (`dbfilter`) | Fix config, or fall back to v1 | no |
| 400 | `-32001` | v1 | `action` not in the allowlist | Client bug — fix the action value | no |
| 400 | `-32002` | v1 | `call_method` missing `fn_name` | Provide a non-empty `fn_name` | no |
| 400 | `-32007` | v2 | `model_id`/`method` not a valid Odoo identifier, or `db`/`api_key` not header-safe. Odoo not contacted | Client bug / bad config | no |
| 401 | `-32000` | both | Invalid / missing `x-api-key` | Fix the **proxy** key (header), not the Odoo key. `id` is `null` | no |
| 403 | `0` | both | Expired / invalid proxy license | Operational — renew the proxy license | no |
| 502 | `-32004` | both | Proxy cannot reach Odoo | Check Odoo connectivity | **yes**, with backoff |
| 504 | `-32003` | both | Odoo call timed out | Raise `x-request-timeout` or retry | **only if idempotent** — the upstream call may still have run |
| 500 | `-32005` | both | Proxy failed to decode Odoo's response | Proxy-side; log and escalate | no |

## Pitfalls

- **HTTP 200 is not success.** Every Odoo-side error arrives on 200 with an
  `error` object. Check `error` before reading `result`.
- **Code `0` is ambiguous on its own.** It is the proxy license error **only on
  HTTP 403**. Odoo 19+ also returns code `0` for every v1 `/jsonrpc` error, on
  HTTP 200 — that is an Odoo logic error. Classify by HTTP status first.
- **Two different 401s.** HTTP 401 / `-32000` is the proxy key. HTTP 200 /
  `401` is the Odoo key. Keep them as separate error types; they have different
  owners (ops vs. the end user).
- **Branch on `data.name`, never on `data.debug`.** On both versions,
  `error.data` is Odoo's error object `{name, message, arguments, context, debug,
  timestamp?}`; `name` is the exception class (e.g.
  `odoo.exceptions.ValidationError`, `odoo.exceptions.AccessError`) and `message`
  is the human-readable text (v1's top-level `message` is just
  `Odoo Server Error`). `debug` is a traceback and may be empty.
- **Don't retry timeouts on writes.** A `-32003` means the proxy stopped
  waiting, not that Odoo stopped working; a retried `create` can duplicate.

## Handling strategy

- **Retryable:** `-32004` and Odoo `409` → bounded exponential backoff.
  `-32003` only for idempotent calls (reads).
- **Fix-the-request:** `-32001`, `-32002`, `-32007`, Odoo `404`, argument `422`s
  → programming errors, fail fast.
- **Fix-the-config:** `-32000` (proxy key), `0`/403 (license), `-32006`
  (version or `dbfilter`) → surface clearly; no retry.
- **End-user action:** Odoo `401` (re-issue the Odoo API key), `403`
  (permissions), validation `422` (show the message).
- **`-32005` / Odoo 5xx:** server-side; log the request `id` and escalate.

Always log the response `id` — it ties client logs to proxy logs.

## How SDKs surface these

All official SDKs do the 200-with-error check internally and keep the original
`code`, `message`, `data` and HTTP status, but the **type names differ per SDK**
(`sdks.md` has each one's exact names):

- **JS/TS, Python, .NET:** a typed class per proxy code, plus Odoo-status
  subclasses of the Odoo-error type (`OdooAuthError`/`OdxOdooAuthException` for
  401, …`Access` 403, …`NotFound` 404, …`Conflict` 409, …`Validation` 422,
  …`Server` 5xx) and `Json2Unavailable…` / `InvalidRequest…` for `-32006` /
  `-32007`.
- **Swift:** one enum `OdxProxyError` with a case per proxy code, plus
  `.json2Unavailable` / `.invalidRequest`; Odoo statuses via `error.odooStatus`.
- **Java/Kotlin and PHP:** one exception type with helpers — `odooStatus`,
  `odooErrorName`, `isLicenseError` (403 only), `isJson2Unavailable`,
  `isInvalidRequest`, `isRetryable`.

None of the SDKs retry on their own.
