# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

This is a **Claude Skills project**, not an application. Its purpose is to make a Claude Code agent effective at two things:

1. **Understanding a target Odoo instance's data structure** by introspecting it through ODXProxy (`fields_get`, `search_read`, etc.).
2. **Helping the user build their application/system** against that Odoo instance — either on top of ODXProxy's official client SDKs or a custom client.

The directory is currently a clean slate: there is no build system, no test suite, and no source code yet. Do not invent build/lint/test commands — none exist until the skill's own tooling is created. When scaffolding is added, document the real commands here.

## ODXProxy: the domain this skill operates on

ODXProxy (https://odxproxy.io, docs at `/docs`) is a Rust reverse proxy exposing **one unified JSON-RPC 2.0 API in front of any number of Odoo instances**. It wraps Odoo's `execute_kw`, enforces a fixed method allowlist, and routes each request to a per-request-specified Odoo backend. Apps talk to the proxy, never to Odoo directly.

**Two distinct API keys — never conflate them:**
- **Proxy key** → `x-api-key` HTTP header (authenticates client → proxy).
- **Odoo user key** → `odoo_instance.api_key` in the request body (authenticates proxy → Odoo).

**Primary endpoint:** `POST /api/odoo/execute`. Request body fields:
`id`, `action`, `model_id`, `fn_name` (only for `call_method`), `params` (positional args to execute_kw), `keyword` (kwargs: `fields`, `limit`, `offset`, `order`, `context`), and `odoo_instance` `{url, db, user_id, api_key}`. Optional header `x-request-timeout` (seconds; default 15). Other endpoints: `POST /api/odoo/version`, `GET /_/license`, `GET /_/about`, `GET /_/metrics` (Prometheus).

**The 9 allowed actions** (the `action` value must match exactly):
`search_count`, `search`, `read`, `fields_get`, `search_read`, `create`, `write`, `unlink`, `call_method` (arbitrary model method — requires a non-empty `fn_name`).

**Response envelope on every status code:** `{ "jsonrpc": "2.0", "id", "result", "error": { "code", "message", "data" } }`.

> **Critical gotcha:** an HTTP `200` can still carry a populated `error` (Odoo logic/permission failures pass through). Always check `error` before reading `result`; never trust HTTP status alone.

**Error codes:** `-32001` (400, action not allowlisted) · `-32002` (400, missing `fn_name`) · `-32000` (401, bad/missing api key) · `0` (403, expired/invalid license) · `-32004` (502, Odoo unreachable) · `-32003` (504, Odoo timeout) · `-32005` (500, decode failure) · Odoo's own errors pass through on 200.

## Reference material (SDK sources)

The real SDK sources live on GitHub under **https://github.com/terrakernel** —
read the actual source rather than guessing. `references/sdks.md` lists the
per-language repo URLs, the verified public API of each, and the cross-SDK drift.
(If you happen to have local clones, read those; don't assume any fixed local
path.) Published SDKs: Python (`ODXProxyClient-Python`, import `odxproxy`),
Java/Kotlin (`ODXProxyClient-Java`, pkg `io.odxproxy`), PHP (`ODXProxyClient-PHP`,
`odxproxy/client`), Kotlin (`odxproxy-kotlin`, pkg `com.terrakernel`), Swift
(`ODXProxyClient-Swift`), JS/TS (`odxproxy-client-js`,
`@terrakernel/odxproxy-client-js`), and .NET/C# (`ODXProxyClient-Net`, NuGet
[`TerraKernel.OdxClient`](https://www.nuget.org/packages/TerraKernel.OdxClient)
v1.0.0, .NET 10). A Dart client exists but is **not published yet** — don't
recommend it.

## SDK client shape — shared intent, but NOT uniform

All SDKs share the same intent: hold the proxy URL + `x-api-key` once, bind an
Odoo instance's credentials, expose one method per allowed action, and turn
JSON-RPC errors into typed exceptions (preserving code/message/data). **In
practice the APIs have drifted** — class names, init patterns, method names, and
error types differ per language, and none match the shape shown on the website's
SDK docs. Concrete examples: `unlink` is `remove` in JS/Java/Swift; `call_method`
is `call` in PHP; the JVM has two separate clients (`io.odxproxy` high-level vs
`com.terrakernel` low-level); JS is the only SDK whose error class names match
the website. **.NET breaks the shape entirely**: a Rust C-ABI native core behind
an AOT-friendly binding, with no per-action methods — one `ExecuteAsync` plus an
`OdxAction` enum, `params`/`keyword` supplied as raw JSON bytes, async only.
**Always read the specific SDK's source before writing against it.**
Full per-language APIs, a drift table, and remote git URLs are in
`references/sdks.md`. The raw HTTP/JSON-RPC contract (`references/api-reference.md`)
is stable regardless of SDK drift — use it for custom clients.
