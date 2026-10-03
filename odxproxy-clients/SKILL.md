---
name: odxproxy-clients
description: >-
  Use when building an application, integration, or bot that talks to an Odoo
  ERP through ODXProxy — the Rust JSON-RPC proxy at odxproxy.io. Covers both
  API versions: v1 (/api/odoo/execute, execute_kw over /jsonrpc, any Odoo up to
  21, the 9 allowed actions search_read, search, read, fields_get, create,
  write, unlink, search_count, call_method) and v2 (/v2/odoo/execute, Odoo
  JSON-2, Odoo 19+ and required on 22+, model_id + method + named kwargs);
  choosing between them; the request/response envelope; error handling; the
  official SDKs (Python, JavaScript/TS, Java/Kotlin, PHP, Swift, .NET/C# via
  NuGet TerraKernel.OdxClient); and introspecting a target Odoo instance's data
  model (fields_get / relations) before writing code. Trigger on: ODXProxy,
  odxproxy, Odoo via proxy, execute_kw over JSON-RPC, JSON-2, /v2/odoo,
  for_instance / for_instance_v2, OdxClient/OdxAction/OdxProxyV2/OdxApiV2,
  x-api-key + Odoo api_key, Odoo 19/20/22 API migration, building an Odoo
  client/app.
---

# ODXProxy Clients

Help the user build applications against an Odoo ERP **through ODXProxy**, and
understand the target Odoo instance's data structure first so the code matches
reality.

## Mental model (read this first)

ODXProxy is a Rust reverse proxy exposing **one JSON-RPC 2.0 API** in front of
any number of Odoo instances. Apps call the proxy; the proxy calls Odoo. Three
facts drive almost every mistake:

1. **Two separate keys.** The proxy key goes in the `x-api-key` HTTP header
   (client → proxy). The Odoo user key goes in the request body as
   `odoo_instance.api_key` (proxy → Odoo). They are never the same value.
2. **HTTP 200 can still be an error.** Odoo logic/permission failures come back
   inside a populated `error` object on a 200 response. Always inspect `error`
   before reading `result`.
3. **There are two API versions, and their argument shapes don't mix.**

| | v1 — `POST /api/odoo/execute` | v2 — `POST /v2/odoo/execute` |
|---|---|---|
| Odoo | any version up to 21 (22 removes `/jsonrpc`) | **19+**, the only option on 22+ (needs ODXProxy 0.9.0+) |
| Upstream | `execute_kw` over `/jsonrpc` | Odoo JSON-2 |
| Call | `action` (9-action allowlist) + positional `params` + `keyword` | `model_id` + any public `method` + one named `kwargs` object |
| Instance | `url`, `db`, `user_id`, `api_key` | `url`, `db`, `api_key` (no `user_id`) |

v1 is not deprecated — it's the only way to reach Odoo ≤18. Minimal bodies:

```json
// v1
{ "id": "req-1", "action": "search_read", "model_id": "res.partner",
  "params": [[["is_company", "=", true]]],
  "keyword": { "fields": ["id", "name", "email"], "limit": 20 },
  "odoo_instance": { "url": "https://erp.example.com", "db": "prod", "user_id": 2, "api_key": "<odoo user key>" } }

// v2
{ "id": "req-1", "model_id": "res.partner", "method": "search_read",
  "kwargs": { "domain": [["is_company", "=", true]], "fields": ["id", "name", "email"], "limit": 20 },
  "odoo_instance": { "url": "https://erp.example.com", "db": "prod", "api_key": "<odoo user key>" } }
```

Note the domain: wrapped in v1's positional `params`, bare in v2's `kwargs`.
v2 keys are **Odoo's Python parameter names, verbatim** (`vals_list`, `ids`,
`allfields` — never camelCased); `create` always takes and returns a list.
Full contracts live in `references/` — load them as needed rather than guessing.

## Workflow

**1. Pick the API version per Odoo instance.** Ask or detect the Odoo version:

- ≤18 → v1. 22+ → v2. 19–21 → either; prefer v2 for new code that must
  survive an upgrade to 22, v1 if the same code must also reach older instances.
- Unknown → `python scripts/odx.py --v2 version` (or the SDK's
  `supports_v2`/`isSupported`): major ≥ 19 → v2; `-32006` → v1.
- v2 caveats that bite in production: the Odoo key must be an **API key** (not a
  password; scope `rpc` on Odoo 20+) and non-admin keys **expire**; hosts that
  pick the database from the hostname (`dbfilter`) need `url` to be that
  database's own hostname, or calls fail with `-32006`; company selection needs
  `context.allowed_company_ids`. Details: `references/api-reference.md`.

**2. Discover the target Odoo model with `fields_get` — before serializing into
the native language.** Do not assume field names; Odoo models are heavily
customized per instance. **Always call `fields_get` on the model first** to get
its real schema (field names, `type`, `required`, `relation`, `selection`),
*then* map that schema into your target language's native types
(structs/classes/DTOs/models). Writing the native data model before introspecting
is the most common source of bugs.

- Every official SDK exposes `fields_get` first-class on both versions.
- No SDK yet (or just exploring)? `scripts/odx.py` is a zero-dependency CLI
  over the proxy: `fields_get`, `search_read`, and every other call, on v1 by
  default or v2 with `--v2`.
- Then sample a few real records with `search_read` to confirm value shapes
  (many2one as `[id, "name"]`, empty values as `false`, and on Odoo 20+ binary
  fields as `{content, filename, size}`).
- Full recipe — classify fields, follow relations, map the model graph:
  `references/odoo-introspection.md`.

If you have no live instance, say so and design against documented Odoo core
models, flagging every field the user must confirm.

**3. Pick the client path.** Either an official SDK or a hand-rolled client:

- Official SDKs (Python, JS/TS, Java/Kotlin, PHP, Swift, .NET) all support both
  versions, with v2 as a separate session/namespace (`for_instance_v2`,
  `v2.*`, `OdxProxyV2`, `Odx::v2()`, `OdxApiV2`, `ForInstanceV2`). Each kept its
  own v1 naming (`remove` vs `unlink`, `call` vs `call_method`, snake vs
  camel), and JS, Java and Swift are **process singletons** (one Odoo instance
  per process). .NET is Windows 11 x64 only. Read `references/sdks.md`, then
  the real SDK source/README for the installed version.
- Custom client: implement the envelope and the 200-with-error check yourself.
  Contract is in `references/api-reference.md`.

**4. Build, mapping each user operation to one call.** v1: one of the 9
actions, with `call_method` + `fn_name` for anything beyond CRUD (e.g.
`action_confirm`). v2: the Odoo method by name, `ids` only for record methods,
every other argument named. Per-call shapes for both: `references/actions.md`.

**5. Handle errors by code, not by HTTP status alone.** Codes `100`–`599` are
Odoo HTTP statuses (v2: `401` expired Odoo key, `403`, `404`, `409` retryable,
`422` validation/bad args); `0` and negatives are the proxy's. Keep the proxy's
401 (`-32000`) separate from Odoo's `401`; code `0` is a license error only on
HTTP 403. Retry only `-32004`, `409`, and `-32003` for idempotent reads.
Catalog: `references/errors.md`.

## Reference index

| File | Use when |
|------|----------|
| `references/api-reference.md` | Endpoints, v1 vs v2, envelope, v2 caveats; building a custom client |
| `references/actions.md` | v1 `params`/`keyword` per action and v2 `kwargs` per method |
| `references/errors.md` | Mapping error codes (both versions) to handling and retries |
| `references/sdks.md` | Choosing/using an official SDK; v1 and v2 entry points and names per language |
| `references/odoo-introspection.md` | Discovering the target Odoo's data model |
| `scripts/odx.py` | Live calls against a proxy for introspection/testing (`--v2` for JSON-2) |

## SDK sources

The official SDK sources live on GitHub under **https://github.com/terrakernel**
(per-language repo URLs are in `references/sdks.md`). There is no Dart SDK yet
— use the raw contract. Before relying on exact symbol names, read the real
source of the SDK the user is on — browse/clone its repo, or read a local
checkout if you have one — because this skill's summaries can drift from the
code.
