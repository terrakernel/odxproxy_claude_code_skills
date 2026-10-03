# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

This is a **Claude Skills project**, not an application. Its purpose is to make a Claude Code agent effective at two things:

1. **Understanding a target Odoo instance's data structure** by introspecting it through ODXProxy (`fields_get`, `search_read`, etc.).
2. **Helping the user build their application/system** against that Odoo instance — either on top of ODXProxy's official client SDKs or a custom client.

Layout: `SKILL.md` (entry point, loaded first — keep it short; the description must stay ≤1024 characters), `references/*.md` (loaded on demand), `scripts/odx.py` (zero-dependency Python CLI). There is no build system, lint or test suite. Verify `odx.py` changes by running it against a real ODXProxy (≥0.9.0 for `--v2`) in front of an Odoo 19+ instance, for both v1 and `--v2`, including the error paths.

## ODXProxy: the domain this skill operates on

ODXProxy (https://odxproxy.io, docs at `/docs`; wire spec in the proxy repo's `SYSTEM_ARCHITECTURE.md`) is a Rust reverse proxy exposing **one unified JSON-RPC 2.0 API in front of any number of Odoo instances**. Apps talk to the proxy, never to Odoo directly. It has **two API versions**:

- **v1** — `POST /api/odoo/execute` (alias `/v1/odoo/execute`): wraps Odoo's `execute_kw` over `/jsonrpc`, works on any Odoo up to 21. Body: `id`, `action` (one of 9: `search_count`, `search`, `read`, `fields_get`, `search_read`, `create`, `write`, `unlink`, `call_method` + `fn_name`), `model_id`, `params` (positional args), `keyword` (kwargs), `odoo_instance {url, db, user_id, api_key}`.
- **v2** — `POST /v2/odoo/execute` (ODXProxy 0.9.0+): Odoo's JSON-2 API, Odoo 19+, the only option on 22+ (Odoo removes `/jsonrpc`). Body: `id`, `model_id`, `method` (any public method, no allowlist), `kwargs` (one object of named args under Odoo's Python parameter names), `odoo_instance {url, db, api_key}` (no `user_id`). `create` always takes/returns a list. Database selection follows the server's `dbfilter`.

v1 is not deprecated (it's the only path to Odoo ≤18). Version endpoints: `POST /api/odoo/version`, `POST /v2/odoo/version` (`{version_info, version}`). Ops: `GET /_/license`, `GET /_/about`, `GET /_/metrics`. Optional header `x-request-timeout` (seconds; default 15).

**Two distinct API keys — never conflate them:**
- **Proxy key** → `x-api-key` HTTP header (authenticates client → proxy).
- **Odoo user key** → `odoo_instance.api_key` in the request body (authenticates proxy → Odoo). On v2 it must be an API key (not a password), and non-admin keys expire.

**Response envelope on every status code:** `{ "jsonrpc": "2.0", "id", "result", "error": { "code", "message", "data" } }`.

> **Critical gotcha:** an HTTP `200` can still carry a populated `error` (Odoo logic/permission failures pass through). Always check `error` before reading `result`; never trust HTTP status alone.

**Error codes:** proxy codes are `0` and negatives — `-32000` (401, bad api key), `0` (403 only: license), `-32001`/`-32002` (400, v1 action/fn_name), `-32007` (400, v2 invalid identifier), `-32006` (200, v2: no JSON-2 or `dbfilter`), `-32004` (502), `-32003` (504), `-32005` (500). Codes `100`–`599` on HTTP 200 are Odoo's HTTP status on v2 (`401`, `403`, `404`, `409`, `422`, `5xx`). v1 Odoo errors are code `0` on Odoo 19+ (`200` on older), on HTTP 200.

## Reference material (SDK sources)

The real SDK sources live on GitHub under **https://github.com/terrakernel** — read the actual source rather than guessing. `references/sdks.md` lists packages, repo URLs, and each SDK's v1/v2 entry points and error types. Published SDKs (all with v1 + v2): Python `terrakernel-odxproxyclient` 0.9.0+, JS/TS `@terrakernel/odxproxy-client-js` 0.9.0+, Java/Kotlin `io.odxproxy:odxproxyclient-java` 0.9.0+, PHP `odxproxy/client` 0.9.0+, Swift `ODXProxyClient-Swift` 1.1.0+, .NET `TerraKernel.OdxClient` 1.1.0+ (Windows 11 x64 only). There is no separate Kotlin SDK (use the Java one, which is written in Kotlin) and no published Dart SDK — don't recommend either.

## SDK client shape

All SDKs hold the proxy URL + `x-api-key` once, bind an Odoo instance, expose one method per operation, and raise typed errors keeping code/message/data. v1 APIs drifted per language (`remove` vs `unlink`, `call` vs `call_method`, snake vs camel; .NET v1 is one `ExecuteAsync` + `OdxAction` enum with raw JSON). v2 was added to all of them from one spec (`SYSTEM_ARCHITECTURE.md` §7.1 in the proxy repo) as a separate session type/namespace, keeping each SDK's v1 naming but sending identical wire JSON. JS, Java and Swift are process singletons. **Always read the specific SDK's source before writing against it**, and when an SDK releases, re-read its README and update `references/sdks.md`.
