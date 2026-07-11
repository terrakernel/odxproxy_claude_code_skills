# ODXProxy API Reference

Authoritative source: https://odxproxy.io/docs/api . This file is a working
summary — verify against the live docs or the proxy's `/_/about` when in doubt.

## Authentication — two distinct keys

| Key | Where it goes | Authenticates | Configured by |
|-----|---------------|---------------|---------------|
| Proxy API key | `x-api-key` HTTP header | client → proxy | proxy env `PROXY_API_KEY` |
| Odoo user API key | `odoo_instance.api_key` in body | proxy → Odoo | per Odoo user |

Never send the Odoo key in the header or the proxy key in the body.

## Endpoints

### `POST /api/odoo/execute` (primary)

Headers: `x-api-key` (required), `Content-Type: application/json`, and optional
`x-request-timeout` (integer seconds; overrides the default 15s Odoo timeout).

Request body:

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

Status codes seen: 200, 400, 401, 403, 500, 502, 504.

### `POST /api/odoo/version`

Body `{ "id": "string", "url": "string" }`. Returns Odoo version info in the
same JSON-RPC envelope. Status: 200, 401.

### `GET /_/license`

No auth. Returns `{ "licensee", "valid_until", "is_valid" }`.

### `GET /_/about`

Proxy build/metadata in a JSON-RPC envelope.

### `GET /_/metrics`

Prometheus metrics as `text/plain`.

## Response envelope (every status code)

```json
{
  "jsonrpc": "2.0",
  "id": "string",          // echoed from the request
  "result": null,          // success payload, or null when error is set
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
   validation and permission errors arrive here. Only read `result` when
   `error` is absent.

Because of step 2, checking `response.ok` / `status == 200` alone is a bug.

See `errors.md` for the full code catalog and `actions.md` for per-action
`params`/`keyword` shapes.
