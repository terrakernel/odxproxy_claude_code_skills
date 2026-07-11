---
name: odxproxy-clients
description: >-
  Use when building an application, integration, or bot that talks to an Odoo
  ERP through ODXProxy — the Rust JSON-RPC proxy at odxproxy.io. Covers the
  9 allowed actions (search_read, search, read, fields_get, create, write,
  unlink, search_count, call_method), the request/response envelope, error
  handling, the official SDKs (Python, Java, PHP, Kotlin, Swift, Dart, .NET,
  JavaScript), and how to introspect a target Odoo instance's data model
  (fields_get / relations) before writing code. Trigger on: ODXProxy, odxproxy,
  Odoo via proxy, execute_kw over JSON-RPC, "for_instance", x-api-key + Odoo
  api_key, building an Odoo client/app.
---

# ODXProxy Clients

Help the user build applications against an Odoo ERP **through ODXProxy**, and
understand the target Odoo instance's data structure first so the code matches
reality.

## Mental model (read this first)

ODXProxy is a Rust reverse proxy exposing **one JSON-RPC 2.0 API** in front of
any number of Odoo instances. Apps call the proxy; the proxy calls Odoo's
`execute_kw`. Two facts drive almost every mistake:

1. **Two separate keys.** The proxy key goes in the `x-api-key` HTTP header
   (client → proxy). The Odoo user key goes in the request body as
   `odoo_instance.api_key` (proxy → Odoo). They are never the same value.
2. **HTTP 200 can still be an error.** Odoo logic/permission failures come back
   inside a populated `error` object on a 200 response. Always inspect `error`
   before reading `result`.

Endpoint: `POST /api/odoo/execute`. Only **9 actions** are allowed through:
`search_count`, `search`, `read`, `fields_get`, `search_read`, `create`,
`write`, `unlink`, `call_method` (arbitrary method — needs `fn_name`).

Minimal request body:

```json
{
  "id": "req-1",
  "action": "search_read",
  "model_id": "res.partner",
  "params": [[["is_company", "=", true]]],
  "keyword": { "fields": ["id", "name", "email"], "limit": 20 },
  "odoo_instance": { "url": "https://erp.example.com", "db": "prod", "user_id": 2, "api_key": "<odoo user key>" }
}
```

`params` = positional args to `execute_kw`; `keyword` = kwargs (`fields`,
`limit`, `offset`, `order`, `context`, ...). Full field/type details, all
actions, and the error catalog live in `references/` — load them as needed
rather than guessing.

## Workflow

**1. Discover the target Odoo model with `fields_get` — before serializing into
the native language.** Do not assume field names; Odoo models are heavily
customized per instance. **Always call `fields_get` on the model first** to get
its real schema (field names, `type`, `required`, `relation`, `selection`),
*then* map that schema into your target language's native types
(structs/classes/DTOs/models). Writing the native data model before introspecting
is the most common source of bugs.

- Every official SDK exposes a `fields_get` method by default — use the SDK's
  own `fields_get` when working inside a chosen SDK. `call_method` is **not**
  needed for this; `fields_get` is one of the 9 first-class actions.
- No SDK yet (or just exploring)? `scripts/odx.py` is a zero-dependency CLI over
  `/api/odoo/execute` for running `fields_get` and `search_read` against the
  live instance.
- Then sample a few real records with `search_read` to confirm value shapes
  (e.g. many2one as `[id, "name"]`, which selection values actually occur).
- Full recipe — classify fields, follow relations, map the model graph:
  `references/odoo-introspection.md`.

If you have no live instance, say so and design against documented Odoo core
models, flagging every field the user must confirm.

**2. Pick the client path.** Either an official SDK or a hand-rolled client:

- Official SDKs all share one shape: hold proxy URL + `x-api-key` once, bind an
  Odoo instance with `for_instance(...)`, call one method per action, catch
  typed exceptions. Language specifics + local source paths:
  `references/sdks.md`.
- Custom client: implement the envelope and the 200-with-error check yourself.
  Contract is in `references/api-reference.md`.

**3. Build, mapping each user operation to one allowed action.** If an operation
needs an Odoo method outside the 8 CRUD actions (e.g. `action_confirm`), use
`call_method` with `fn_name`. Details + per-action param shapes:
`references/actions.md`.

**4. Handle errors by code, not by HTTP status alone.** Map the JSON-RPC error
codes to user-facing behavior (retry on timeout, surface Odoo validation
messages, fail fast on auth/license). Catalog: `references/errors.md`.

## Reference index

| File | Use when |
|------|----------|
| `references/api-reference.md` | Full endpoint + envelope contract; building a custom client |
| `references/actions.md` | Exact `params`/`keyword` shape for each of the 9 actions |
| `references/errors.md` | Mapping error codes to handling logic |
| `references/sdks.md` | Choosing/using an official SDK; local reference repo paths |
| `references/odoo-introspection.md` | Discovering the target Odoo's data model |
| `scripts/odx.py` | Running live calls against a proxy for introspection/testing |

## Local reference repos

The official SDK sources live on GitHub under **https://github.com/terrakernel**
(per-language repo URLs are in `references/sdks.md`). Published SDKs: Python,
Java (Kotlin), PHP, Kotlin, Swift, and JavaScript/TS. Dart and .NET exist but are
**not published yet** — don't recommend them. Before relying on exact symbol
names, read the real source of the SDK the user is on — browse/clone its repo, or
read a local checkout if you have one — because this skill's summaries can drift
from the code.
