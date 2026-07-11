# Official SDKs

> **Ground-truth rule:** the published docs at `odxproxy.io/docs/sdks/*` and the
> SDK repos (github.com/terrakernel) have **drifted** — different class names,
> package names, and API shapes, and the SDKs differ from each other too (see the
> drift table below). Before writing client code, **read the actual source of the
> SDK version the user is on**. Treat this file as a map, not an API contract.

## Repos, packages, and remote git URLs

GitHub org: **https://github.com/terrakernel**. Use the remote URL to refresh
this knowledge when an SDK changes — `git ls-remote <url>` for tags, or clone /
browse to re-read the client + models + exceptions. URLs marked *(confirmed)*
come from the local repo's `git remote`; the rest are inferred from the org
naming convention and should be verified before relying on them.

| Language | Local repo | Package / coordinates | Remote git URL |
|----------|-----------|-----------------------|----------------|
| Python | `odxproxyclient-py` | dist+import `odxproxy` (v0.1.0), httpx + Pydantic v2, ULID | `https://github.com/terrakernel/ODXProxyClient-Python` *(verified reachable)* |
| Java (Kotlin) | `odxproxyclient-java` | `io.odxproxy:odxproxyclient-java:0.1.0`, OkHttp + Jackson | `https://github.com/terrakernel/ODXProxyClient-Java` *(confirmed)* |
| PHP | `odxproxyclient-php` | composer `odxproxy/client`, cURL | `https://github.com/terrakernel/ODXProxyClient-PHP` *(confirmed)* |
| Kotlin | `odxproxy-kotlin` | group `com.terrakernel` | *(no public repo found under `ODXProxyClient-Kotlin`; local has no remote — ask the user for the URL)* |
| Swift | `ODXProxyClient-Swift` | SwiftPM, module `ODXProxyClientSwift` | `https://github.com/terrakernel/ODXProxyClient-Swift` *(confirmed)* |
| JavaScript / TS | *(not local — clone remote)* | npm `@terrakernel/odxproxy-client-js` (v0.1.7), fetch-based, bundled TS types | `https://github.com/terrakernel/odxproxy-client-js` *(confirmed)* |

Dart and .NET clients exist locally (`ODXProxyClient-Dart`, `ODXProxyClient-Net`)
but are **not published yet** — treat them as WIP, not shippable SDKs, and don't
recommend them until released.

> **Two distinct JVM clients exist** — don't conflate them: `odxproxyclient-java`
> (package `io.odxproxy`) is a **high-level** client with named action methods,
> while `odxproxy-kotlin` (package `com.terrakernel`) is a **low-level**
> `postRequest`-based client with no per-action helpers.

## Shared design intent

All SDKs are meant to: hold the proxy URL + `x-api-key` once, bind a target
Odoo instance's credentials, expose one method per allowed action, and turn
JSON-RPC errors into typed exceptions that keep the original code/message/data.
The 200-with-error check (see `api-reference.md`) is done inside the SDK.

## Drift at a glance (verified against local source)

Method/shape naming is **not** uniform — always check the specific SDK:

| Concept | Python | Java (`io.odxproxy`) | PHP | Swift | Kotlin (`com.terrakernel`) | JS/TS |
|---------|--------|----------------------|-----|-------|-----------------------------|-------|
| Init | `OdxClient(config, context)` per-instance | singleton `OdxProxyClient.init()` / facade `OdxProxy` | `new OdxProxyClient(config)` or static `Odx::init/with` | singleton `OdxProxyClient.configure(with:)`, `OdxApi` statics | `OdxProxyClient.getInstance(info)` | singleton `init(options)` + module funcs |
| `unlink` action | `unlink` | **`remove`** | `unlink` | **`remove`** | *(none — build request)* | **`remove`** |
| `call_method` | `call_method` | `callMethod(fn_name)` | **`call(model, method, args)`** | `callMethod(functionName:)` | *(none)* | `call_method(model, params, keyword, function_name)` |
| Async | async (httpx) | callback/sync (OkHttp) | sync (cURL) | `async throws` | `suspend` (coroutines) | `Promise` (fetch) |
| Errors | `OdxServerErrorException` (base `OdxError`) | `OdxServerErrorException` (RuntimeException) | `OdxException` (RuntimeException) | **rich enum `OdxProxyError`** (per-code cases) | via `OdxServerResponse.error` | **typed subclasses of `OdxError`** (per-code) |
| Named actions? | yes | yes | yes | yes | **no (low-level)** | yes (functional) |

The **JS SDK is the only one whose error class names match the website docs**
(`AuthError`, `OdooLogicError`, `OdooTimeoutError`, …) — the website's SDK docs
appear modeled on it. None of the JVM/Python/PHP SDKs use that naming; Swift's
enum is closest in spirit but with different case names. Method naming also
varies: JS uses **snake_case** (`search_read`, `fields_get`, `call_method`),
Java/Swift use **camelCase**, and `unlink` is exposed as `remove` in JS, Java,
and Swift.

## Python — actual local API (`odxproxyclient-py` v0.1.0)

The real local client is **async** and splits config from per-request context:

```python
from odxproxy import OdxClient
from odxproxy.models import OdxGatewayConfig, OdxUserContext, OdxClientKeywordRequest
from odxproxy.exceptions import OdxServerErrorException

config  = OdxGatewayConfig(gateway_url="https://proxy", gateway_api_key="<proxy x-api-key>")
context = OdxUserContext(instance=...)  # carries the odoo_instance (url/db/user_id/api_key)

client = OdxClient(config, context)  # lightweight; fine to build per HTTP request
ids = await client.search("res.partner", [["is_company", "=", True]], OdxClientKeywordRequest(limit=50))
```

- Methods (all async, keyword `req_id` optional): `search(model, domain, keyword)`,
  `search_read(model, domain, keyword, result_type)`, `read(model, ids, keyword, result_type)`,
  `search_count(model, domain, keyword)`, `create`, `write`, `unlink`,
  `call_method`. `search_read`/`read` take a `result_type` (a Pydantic model) and
  return typed records via `TypeAdapter`.
- `keyword` is an `OdxClientKeywordRequest` (fields/limit/offset/order/context);
  `search`/`read`/`search_count` reset pagination internally.
- Errors: a single `OdxServerErrorException(code, message, data)` (base
  `OdxError`) is raised for both transport-level non-200s and 200-with-error
  responses. Network errors → code `599`; empty/invalid → `500`.
- `contrib/` has Django, FastAPI, and Flask integration helpers.

> The website docs show a different, sync+async `ODXProxyClient` with
> `for_instance(...)` and `AuthError`/`OdooLogicError`/`OdooTimeoutError`. That
> is either a newer or aspirational published API. **Confirm which one the
> user has installed** (`pip show odxproxy` / read the installed package) before
> writing against either shape.

## Java — actual local API (`odxproxyclient-java`, package `io.odxproxy`)

Written in **Kotlin**, published as `io.odxproxy:odxproxyclient-java`. OkHttp +
Jackson. Uses a **singleton** + a static facade `OdxProxy`:

- Init once: `OdxProxyClient.init(options: OdxProxyClientInfo)` (throws if
  already initialized); retrieve with `OdxProxyClient.getInstance()`.
- Actions via `OdxProxy`: `search`, `searchRead<T>`, `read<T>`, `searchCount`,
  `create<T>`, `write`, **`remove`** (this is `unlink`), `fieldsGet<T>`,
  `callMethod<T>`. Generic `<T>` methods deserialize into your model type.
- Errors: `OdxServerErrorException` (a `RuntimeException`) carrying code/message/
  data.

## PHP — actual local API (`odxproxyclient-php`, composer `odxproxy/client`)

Synchronous, cURL-based. Two entry styles:

- Instance: `new OdxProxyClient(OdxClientConfig $config)`.
- Static facade: `Odx::init([...])` / `Odx::with([...])` then `Odx::search(...)`.
- Methods: `search`, `searchCount`, `searchRead`, `read`, `create`, `write`,
  `unlink`, **`call(model, method, args, kw)`** (this is `call_method`), and a
  low-level `execute(...)`.
- Errors: `OdxException extends \RuntimeException`, constructed with
  `(int $code, string $message, ?array $data)`.

## Swift — actual local API (`ODXProxyClient-Swift`, module `ODXProxyClientSwift`)

`async throws`, singleton configuration, and the **richest error typing** of all
the SDKs:

- Configure once: `OdxProxyClient.configure(with: OdxProxyClientInfo, timeout:)`.
- Actions via `OdxApi` statics, each `async throws` returning
  `OdxServerResponse<T>`: `search`, `searchRead<T>`, `read<T>`, `fieldsGet<T>`,
  `searchCount`, `create<T>`, `write<T>`, **`remove<T>`** (this is `unlink`),
  `callMethod<T>(functionName:)`. Ops helpers: `OdxOps.about()`, `.license()`.
- Errors: enum `OdxProxyError` with granular cases mapped to the catalog —
  `.authFailure` (-32000), `.invalidAction` (-32001), `.missingFunctionName`
  (-32002), `.upstreamTimeout` (-32003), `.upstreamConnect` (-32004),
  `.proxyInternal` (-32005), `.licenseInvalid` (0/403), `.odooLogic` (200+error),
  plus transport cases (`.notConfigured`, `.networkError`, `.decodingError`, …).
  Best reference for mapping codes → behavior in any language.

## Kotlin — actual local API (`odxproxy-kotlin`, package `com.terrakernel`)

A deliberately **low-level** coroutine client — no per-action helpers. You build
an `OdxClientRequest` and call:

- `OdxProxyClient.getInstance(info: OdxProxyClientInfo)`.
- `suspend fun postRequest<T>(request): OdxServerResponse<T>` (reified + `Type`
  overloads), `postRequestAny(request)`, and companion `postRaw(...)`.
- Result carries `OdxServerResponse.error` (an `OdxServerErrorResponse`) — check
  it yourself. Prefer `io.odxproxy` (the "Java" client) if you want named
  actions on the JVM.

## JavaScript / TypeScript — actual API (`@terrakernel/odxproxy-client-js` v0.1.7)

`npm install @terrakernel/odxproxy-client-js`. Runs in Node 18+ and browsers
(uses `fetch`/`AbortController`); ships TS types. The **most mature and
faithful** SDK — its error classes match the website docs, and it's on 0.1.7 vs
0.1.0 for the others. Two ways to use it:

- **Functional (recommended):** `init(options)` once, then call module-level
  helpers:
  ```ts
  import { init, search_read, fields_get, create, remove, AuthError, OdooLogicError } from "@terrakernel/odxproxy-client-js";

  init({
    instance: { url: "https://erp", db: "prod", user_id: 2, api_key: "<odoo user key>" },
    odx_api_key: "<proxy x-api-key>",      // proxy key (NOT the Odoo key)
    gateway_url: "https://gateway.odxproxy.io",  // optional; this is the default
    default_timeout_secs: 15,              // optional; sent as x-request-timeout
  });

  const res = await search_read("res.partner", [["is_company", "=", true]],
                                { fields: ["id", "name"], limit: 50, context: { tz: "UTC" } });
  const partners = res.result;
  ```
  Helpers: `search`, `search_read`, `read`, `fields_get`, `search_count`,
  `create`, `write` (+ deprecated alias `update`), **`remove`** (this is
  `unlink`), `call_method(model, params, keyword, function_name, id?, opts?)`
  — note `function_name` comes **after** params/keyword. Plus `version`,
  `about`, `license`, `metrics`. Each returns `OdxServerResponse & { result?: T }`.
- **Low-level (singleton):** `OdxProxyClient.init(options)` / `getInstance()`
  then `.postRequest<T>(request, opts)`.

Config note: options are `odx_api_key` (proxy key) + `instance.api_key` (Odoo
key); `gateway_url` defaults to `https://gateway.odxproxy.io`. `call_method`
rejects an empty `function_name` client-side with `MissingFnNameError`.

Errors (all extend `OdxError` with `.code .data .httpStatus`, thrown by the
two-step check): `AuthError` (-32000), `InvalidActionError` (-32001),
`MissingFnNameError` (-32002), `OdooTimeoutError` (-32003), `OdooConnectError`
(-32004), `InternalProxyError` (-32005), `LicenseError` (0/403),
`OdooLogicError` (200 + error). Branch with `instanceof`.

## When advising on a language

1. Open that SDK's local repo and read its client + models + exceptions — or
   pull the latest from its **remote git URL** above (`git ls-remote` for tags,
   then browse/clone) if the local copy may be stale.
2. Match the user's installed version, not this summary; naming differs per
   language (see the drift table — e.g. `unlink` vs `remove`, `call_method` vs
   `call`).
3. If building a custom client instead, implement the raw contract in
   `api-reference.md` — it's stable regardless of SDK drift.
