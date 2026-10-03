# ODXProxy API Reference

Authoritative source: https://odxproxy.io/docs/api and the proxy repo's
`SYSTEM_ARCHITECTURE.md`. This file is a working summary — verify against the
live docs or the proxy's `/_/about` when in doubt.

## Two API versions

| | v1 | v2 |
|---|---|---|
| Paths | `/api/odoo/execute`, `/api/odoo/version` (aliases `/v1/odoo/*`) | `/v2/odoo/execute`, `/v2/odoo/version` |
| Upstream | Odoo `execute_kw` over `/jsonrpc` | Odoo **JSON-2**: `POST /json/2/<model>/<method>` |
| Odoo versions | any up to 21 (Odoo 22 removes `/jsonrpc`) | **19 and later**; the only option on 22+ |
| Proxy version | any | **ODXProxy 0.9.0+** |
| Arguments | positional `params` + `keyword` kwargs | **named only**: one `kwargs` object |
| Methods | 9-action allowlist (`call_method` for anything else) | any public model method, no allowlist |
| Odoo credentials | `url`, `db`, `user_id`, `api_key` | `url`, `db`, `api_key` (**no `user_id`**) |

Both use the same proxy auth, headers and JSON-RPC response envelope. **v1 is not
deprecated**: Odoo 18 and older have no JSON-2, so v1 is the only way to reach
them. Odoo 19–21 support both. Pick per instance:

- Known Odoo version → choose directly (≤18 → v1, 22+ → v2, 19–21 → either;
  prefer v2 for new code that must survive an upgrade to 22).
- Unknown → call `POST /v2/odoo/version` once per instance and cache the answer
  per URL: `result.version_info[0] >= 19` → v2. A `-32006` or a major `< 19`
  means v1. Don't probe before every call.

## Authentication — two distinct keys

| Key | Where it goes | Authenticates | Configured by |
|-----|---------------|---------------|---------------|
| Proxy API key | `x-api-key` HTTP header | client → proxy | proxy env `PROXY_API_KEY` |
| Odoo user API key | `odoo_instance.api_key` in body | proxy → Odoo | per Odoo user |

Never send the Odoo key in the header or the proxy key in the body.

On **v2** the Odoo key must be a real **API key** (a password is rejected). On
Odoo 20+ its scope must be `rpc` (the default in the key wizard), and keys of
non-admin users **expire on a schedule** — an expired key surfaces as Odoo error
code `401` on HTTP 200, not as the proxy's `-32000`.

## Headers

`x-api-key` (required), `Content-Type: application/json`, and optional
`x-request-timeout` (integer seconds for the upstream Odoo call; missing, `0` or
non-numeric → the proxy default, 15s). The proxy compresses responses when the
client sends `Accept-Encoding: gzip, br, deflate`.

## v1 endpoints

### `POST /api/odoo/execute` (alias `/v1/odoo/execute`)

```json
{
  "id": "string",            // client-generated request id (echoed back)
  "action": "string",        // one of the 9 allowed actions
  "model_id": "string",      // Odoo model, e.g. "res.partner"
  "fn_name": "string|null",  // required only for call_method
  "params": "array|null",    // positional args to execute_kw (default [])
  "keyword": "object|null",  // kwargs to execute_kw (default {})
  "odoo_instance": {
    "url": "string",         // Odoo base URL
    "db": "string",          // database name
    "user_id": "number",     // Odoo user id
    "api_key": "string"      // Odoo user api key
  }
}
```

`params` and `keyword` are passed straight through to Odoo's
`execute_kw(db, uid, key, model, method, args=params, kwargs=keyword)`. All
pagination/filtering (`limit`, `offset`, `order`, `fields`, `context`) is
therefore just standard Odoo kwargs inside `keyword`; the proxy adds no special
pagination fields of its own.

### `POST /api/odoo/version` (alias `/v1/odoo/version`)

Body `{ "id": "string", "url": "string" }`. No Odoo credentials needed. Returns
Odoo's `version_info` object (`server_version`, `server_version_info`, …) in the
envelope.

## v2 endpoints

### `POST /v2/odoo/execute`

```json
{
  "id": "string",
  "model_id": "res.partner",
  "method": "search_read",
  "kwargs": {
    "domain": [["is_company", "=", true]],
    "fields": ["name", "email"],
    "limit": 100,
    "context": {"lang": "en_US", "allowed_company_ids": [1]}
  },
  "odoo_instance": {
    "url": "https://erp.example.com",
    "db": "prod",
    "api_key": "<odoo user api key>"
  }
}
```

- `model_id`, `method`: only `A-Z a-z 0-9 _ .`, not starting with `.`; anything
  else → HTTP 400 `-32007` before Odoo is contacted. Private methods (`_name`)
  are rejected by Odoo with code `403`.
- `kwargs`: a JSON **object** (default `{}`), forwarded byte-for-byte as the
  upstream body. Keys are the Odoo method's **Python parameter names**; record
  ids go in `"ids"`, and `"context"` applies to the call. Per-method keys are in
  `actions.md`.
- `odoo_instance`: `url`, `db`, `api_key`. A `user_id` from a v1-shaped object is
  ignored, so one instance object can serve both versions. The proxy sends
  `api_key` as `Authorization: Bearer` and `db` as `X-Odoo-Database`.

### `POST /v2/odoo/version`

Same body as v1's version call. Calls Odoo's public `GET /json/version`; the
result has a **different shape** from v1's:

```json
{"version_info": [20, 0, 0, "final", 0, "e"], "version": "20.0+e"}
```

A server without `/json/version` (Odoo ≤18) yields `-32006`.

### v2 caveats

- **`dbfilter` applies.** JSON-2 picks the database by header, filtered by the
  server's `dbfilter`. On hosts that choose the database from the hostname
  (e.g. `dbfilter = ^%d$`, common on multi-tenant hosting), `url` must be that
  database's own hostname, or every call fails with `-32006`. v1 is unaffected.
  A `-32006` from a server you know runs 19+ is a database/`dbfilter` problem,
  not a version problem.
- **`create` always returns a list of ids**, even for a single dict.
- **Company context is not implicit.** Odoo applies no company selection unless
  `context.allowed_company_ids` is sent; `company_dependent` fields then read as
  the API user's default company.

## Ops endpoints (no `x-api-key`)

| Endpoint | Returns |
|---|---|
| `GET /_/license` | flat object `{ "licensee", "valid_until", "is_valid" }` (not an envelope) |
| `GET /_/about` | envelope with `result: { "build", "version" }` — check `version >= 0.9.0` before using v2 |
| `GET /_/metrics` | Prometheus text |

## Response envelope (every status code, both versions)

```json
{
  "jsonrpc": "2.0",
  "id": "string",          // echoed from the request (null if unparseable)
  "result": null,          // success payload, or omitted when error is set
  "error": {               // present on error
    "code": -32000,
    "message": "string",
    "data": null
  }
}
```

`result` and `error` are mutually exclusive.

## The two-step success check (do not skip)

1. If HTTP status is **not 200** → treat as a proxy/transport failure; surface
   the JSON-RPC `error`.
2. If HTTP status **is 200** → still check for an `error` object. Odoo
   validation and permission errors arrive here (on v2, with `error.code` = the
   upstream Odoo HTTP status, e.g. `422`). Only read `result` when `error` is
   absent.

Because of step 2, checking `response.ok` / `status == 200` alone is a bug.

See `errors.md` for the full code catalog and `actions.md` for per-action
`params`/`keyword` (v1) and `kwargs` (v2) shapes.
