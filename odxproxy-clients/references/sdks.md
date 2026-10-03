# Official SDKs

> **Ground-truth rule:** treat this file as a map, not an API contract. Before
> writing client code, **read the README and source of the SDK version the user
> has installed** (the repo URLs are below). The v1 APIs drifted between
> languages; v2 was added to every SDK from one spec, so the v2 surfaces line up
> much better — but argument order and type names still differ per language.

## Packages and repos

GitHub org: **https://github.com/terrakernel**. Use `git ls-remote --tags <url>`
to see the latest tag, then browse or clone to re-read the client, models and
exceptions.

| Language | Install | Import / namespace | v2 since | Repo |
|---|---|---|---|---|
| Python ≥3.12 | `pip install terrakernel-odxproxyclient` | `terrakernel.odxproxyclient` | 0.9.0 | `https://github.com/terrakernel/ODXProxyClient-Python` |
| JavaScript / TS | `npm install @terrakernel/odxproxy-client-js` | `@terrakernel/odxproxy-client-js` | 0.9.0 | `https://github.com/terrakernel/odxproxy-client-js` |
| Java / Kotlin / Android | Maven `io.odxproxy:odxproxyclient-java` | `io.odxproxy` | 0.9.0 | `https://github.com/terrakernel/ODXProxyClient-Java` |
| PHP ≥8.1 | `composer require odxproxy/client` | `OdxProxy\` | 0.9.0 | `https://github.com/terrakernel/ODXProxyClient-PHP` |
| Swift (Apple platforms) | SwiftPM `https://github.com/terrakernel/ODXProxyClient-Swift.git`, product `ODXProxyClientSwift` | `ODXProxyClientSwift` | 1.1.0 | same URL |
| .NET 10 / C# (**Windows 11 x64 only**) | `dotnet add package TerraKernel.OdxClient` | `TerraKernel.OdxClient` | 1.1.0 | `https://github.com/terrakernel/ODXProxyClient-Net` |

Notes:

- **Kotlin:** use the Java SDK — it is written in Kotlin and its API is
  idiomatic from Kotlin (named args, defaults). There is no separate Kotlin SDK
  to recommend.
- **Dart/Flutter:** no published SDK yet. Use the raw contract
  (`api-reference.md`) and say so.
- **Versioning:** Python, JS, Java and PHP track the proxy version (0.9.x);
  Swift and .NET have their own semver. v2 needs **ODXProxy 0.9.0+** on the
  server regardless of SDK version.
- **Swift install URL:** use the repo URL above. (Some Swift README revisions
  show `terrakernel/odxproxyswift.git`, which does not resolve.)

## Shape of each SDK

All SDKs hold the proxy URL + `x-api-key` once, bind one Odoo instance, do the
200-with-error check internally, and raise typed errors that keep
`code`/`message`/`data`/HTTP status. They differ in how state is held:

| SDK | Client lifetime | v1 entry | v2 entry |
|---|---|---|---|
| Python | instance per process; sync `ODXProxyClient` + async `AsyncODXProxyClient` | `client.for_instance(url, db, user_id, api_key)` → `Session` | `client.for_instance_v2(url, db, api_key, context=)` → `SessionV2` / `AsyncSessionV2` |
| JS/TS | **process singleton**: `init(options)` | module functions `search_read(...)` … | `v2` namespace: `v2.search_read(...)` (same `init`) |
| Java/Kotlin | **process singleton**: `OdxProxy.init(config)` (throws if called twice) | static `OdxProxy.*` → `CompletableFuture` | static `OdxProxyV2.*` (same `init`) |
| PHP | `Odx::init([...])` global, or `Odx::with($cfg)` per tenant | `Odx::searchRead(...)` … | `Odx::v2()` / `Odx::with($cfg)->v2()` → `OdxV2Client` |
| Swift | **singleton**: `OdxProxyClient.shared.configure(with:)` | `OdxApi.*` statics, `async throws` | `OdxApiV2.*` statics (same configure) |
| .NET | `OdxClient.Create(baseUrl, apiKey)` (IDisposable; reuse) + per-call `OdooInstance` | `client.ExecuteAsync(OdxAction.X, …)` with raw JSON | `client.ForInstanceV2(url, db, apiKey, context)` → `OdxSessionV2` |

The singleton SDKs (JS, Java, Swift) bind **one Odoo instance per process**. For
multi-tenant servers prefer Python, PHP (`Odx::with`) or .NET, or the raw contract.

## v2 method names per SDK

Each SDK kept its own v1 naming in v2. All send the exact wire keys from
`actions.md` (`domain`, `fields`, `vals_list`, `ids`, …) and omit unset args.

| Operation | Python | JS/TS | Java/Kotlin | PHP | Swift | .NET |
|---|---|---|---|---|---|---|
| search_read | `search_read` | `v2.search_read` | `searchRead` | `searchRead` | `searchRead` | `SearchReadAsync<T>` |
| search | `search` | `v2.search` | `search` | `search` | `search` | `SearchAsync` |
| search_count | `search_count` | `v2.search_count` | `searchCount` | `searchCount` | `searchCount` | `SearchCountAsync` |
| read | `read` | `v2.read` | `read` | `read` | `read` | `ReadAsync<T>` |
| fields_get | `fields_get` | `v2.fields_get` | `fieldsGet` | `fieldsGet` | `fieldsGet` | `FieldsGetAsync<T>` |
| create → ids | `create` | `v2.create` | `create` | `create` | `create` | `CreateAsync` |
| create → id | `create_one` | `v2.create_one` | `createOne` | `createOne` | `createOne` | `CreateOneAsync` |
| write | `write` | `v2.write` | `write` | `write` | `write` | `WriteAsync` |
| unlink | `unlink` | **`v2.remove`** | **`remove`** | `unlink` | **`remove`** | `UnlinkAsync` |
| any method | `call_method(model, method, ids=, kwargs=)` | `v2.call_method(model, method, {ids?, …kwargs})` | `callMethod(model, method, T.class, ids=, kwargs=)` | `call(model, method, $kwargs, ids:)` | `callMethod(model:method:ids:kwargs:)` | `CallMethodAsync<T>(model, method, type, ids:, kwargs:)` |
| version | `client.odoo_version_v2(url)` | `v2.version(url?)` | `version(url?)` | `$v2->version()` | `version(url:)` | `client.GetVersionV2Async(url)` |
| v2 available? (cached per URL) | `client.supports_v2(url)` | `v2.is_supported(url?)` | `isSupported(url?)` | `$v2->isSupported()` | `isSupported(url:)` | `client.SupportsV2Async(url)` |

**Session context:** every SDK takes a default Odoo `context` once (`lang`, `tz`,
`allowed_company_ids`) and merges it under each call's own `context` (per-call
keys win). It applies to v2 calls only: Python `for_instance_v2(context=)`, JS
`init({ default_context })`, Java 4th arg of `OdxProxyClientInfo`, PHP config
key `'context'`, Swift `OdxProxyClientInfo(defaultContext:)`, .NET
`ForInstanceV2(context:)`.

## v2 errors per SDK

| SDK | Proxy codes | Odoo statuses (401/403/404/409/422/5xx) |
|---|---|---|
| Python | `AuthError`, `LicenseError`, `OdooTimeoutError`, `OdooConnectError`, `InternalProxyError`, `Json2UnavailableError` (-32006), `InvalidRequestError` (-32007) — base `ODXProxyError` | subclasses of `OdooLogicError`: `OdooAuthError`, `OdooAccessError`, `OdooNotFoundError`, `OdooConflictError`, `OdooValidationError`, `OdooServerError`; `.odoo_error_name` |
| JS/TS | `AuthError`, `LicenseError`, `OdooTimeoutError`, `OdooConnectError`, `InternalProxyError`, `Json2UnavailableError`, `InvalidRequestError` — base `OdxError` (`.code`, `.data`, `.httpStatus`) | same subclass names as Python, under `OdooLogicError`; `.odooErrorName` |
| Java/Kotlin | one `OdxServerErrorException` (`code`, `httpStatus`, `data`) with `isLicenseError`, `isJson2Unavailable`, `isInvalidRequest`, `isRetryable` | `odooStatus` (Int?), `odooErrorName` |
| PHP | one `OdxException` with `rpcCode()`, `httpStatus`, `isLicenseError()`, `isTransportError()`, `isJson2Unavailable()`, `isInvalidRequest()`, `isRetryable()` | `odooStatus()`, `odooErrorName()` |
| Swift | enum `OdxProxyError`: `.authFailure`, `.licenseInvalid`, `.upstreamTimeout`, `.upstreamConnect`, `.proxyInternal`, `.json2Unavailable`, `.invalidRequest`, … | `.odooLogic` + `error.odooStatus`, `error.odooErrorName`, `error.isRetryable` |
| .NET | `OdxAuthException`, `OdxLicenseException`, `OdxUpstreamTimeoutException`, `OdxUpstreamConnectException`, `OdxProxyInternalException`, `OdxJson2UnavailableException`, `OdxInvalidRequestException` — base `OdxException` (`Status`, `RpcCode`, `RpcData`) | subclasses of `OdxOdooException`: `OdxOdoo{Auth,Access,NotFound,Conflict,Validation,Server}Exception`; `OdooErrorName` |

All of them classify code `0` as a license error **only on HTTP 403**, and none
retry automatically.

---

## Python — `terrakernel-odxproxyclient`

Sync and async clients share one core (httpx, HTTP/2 on by default, orjson).
One client per process; sessions are cheap.

```python
from terrakernel.odxproxyclient import ODXProxyClient

with ODXProxyClient(base_url="https://proxy.example.com", api_key="<proxy x-api-key>") as client:
    # v1 — params/keyword forwarded to execute_kw; note the wrapped domain
    s1 = client.for_instance(url="https://erp.example.com", db="prod", user_id=2, api_key="<odoo key>")
    rows = s1.search_read("res.partner", params=[[["is_company", "=", True]]],
                          keyword={"fields": ["name"], "limit": 20})
    s1.call_method("account.move", "action_post", params=[[7]])

    # v2 — named args; the domain is the list itself
    s2 = client.for_instance_v2(url="https://erp.example.com", db="prod", api_key="<odoo key>",
                                context={"lang": "en_US", "allowed_company_ids": [1]})
    rows = s2.search_read("res.partner", [["is_company", "=", True]], fields=["name"], limit=20)
    ids = s2.create("res.partner", [{"name": "Acme"}])        # [42]
    s2.call_method("account.move", "action_post", ids=[7])
    s2.call_method("res.partner", "name_search", kwargs={"name": "Acm", "limit": 5})
```

- Every method takes `request_id=` and `timeout_secs=` (sent as `x-request-timeout`).
- `client.session(OdooInstance(...))` / `client.session_v2(...)` reuse an instance object.
- Ops: `client.about()`, `.license()`, `.metrics()`, `.odoo_version(url)`.
- Return types are `JsonValue` (not narrowed); validate at the call site.

## JavaScript / TypeScript — `@terrakernel/odxproxy-client-js`

Zero runtime deps, `fetch`-based (Node 18+ and browsers), ESM + CJS, bundled
types. **Process singleton** — one Odoo instance per process.

```ts
import { init, search_read, call_method, v2, AuthError, OdooLogicError } from "@terrakernel/odxproxy-client-js";

init({
  instance: { url: "https://erp.example.com", db: "prod", user_id: 2, api_key: "<odoo key>" },
  odx_api_key: "<proxy x-api-key>",
  gateway_url: "https://proxy.example.com",        // default https://gateway.odxproxy.io
  default_timeout_secs: 15,
  default_context: { lang: "en_US", allowed_company_ids: [1] },   // v2 only
});

// v1 — (model, params, keyword, id?, opts?); call_method's function_name comes AFTER keyword
const r1 = await search_read("res.partner", [[["is_company", "=", true]]], { fields: ["name"], limit: 20 });
await call_method("account.move", [[7]], {}, "action_post");

// v2 — (model, options) with Odoo's names; resolves to the envelope, data on .result
const r2 = await v2.search_read("res.partner", { domain: [["is_company", "=", true]], fields: ["name"], limit: 20 });
const ids = (await v2.create("res.partner", [{ name: "Acme" }])).result;   // [42]
await v2.call_method("account.move", "action_post", { ids: [7] });
```

- Helpers resolve to the envelope (`res.result`); failures **throw**.
- `unlink` is **`remove`** (v1 and v2). Trailing `opts`: `{ timeoutSecs, signal }`
  (v2 also `id`). A caller's own aborted `signal` propagates `AbortError` unwrapped.
- v1 extras: `version`, `about`, `license`, `metrics`.

## Java / Kotlin — `io.odxproxy:odxproxyclient-java`

Kotlin compiled to Java 8 bytecode (Android API 24+, Spring, JavaFX); OkHttp 5 +
kotlinx.serialization. **Process singleton.** Every call returns
`CompletableFuture<OdxServerResponse<T>>`.

```kotlin
OdxProxy.init(OdxProxyClientInfo(
    OdxInstanceInfo("https://erp.example.com", 2, "prod", "<odoo key>"),
    "<proxy x-api-key>", "https://proxy.example.com",
    mapOf("lang" to "en_US", "allowed_company_ids" to listOf(1)),   // optional v2 default context
))

// v1 — params are execute_kw's positional args, so the domain is wrapped: [[...]]
// kw = OdxClientKeywordRequest(fields, order, limit, offset, context)
OdxProxy.searchRead("res.partner", listOf(listOf(listOf("is_company", "=", true))),
    OdxClientKeywordRequest(listOf("name"), null, 20, 0, null), null, Partner::class.java)

// v2 — named args (Java: trailing @JvmOverloads params, pass null to skip)
val rows = OdxProxyV2.searchRead("res.partner", Partner::class.java,
    domain = listOf(listOf("is_company", "=", true)), fields = listOf("name"), limit = 20).get().result
val ids = OdxProxyV2.create("res.partner", listOf(mapOf("name" to "Acme"))).get().result   // [42]
OdxProxyV2.callMethod("account.move", "action_post", Boolean::class.javaObjectType, ids = listOf(7)).get()
```

- `unlink` is **`remove`**. The request-id argument: `null` = auto ULID.
- Odoo-quirk types: `OdxMany2One` (`[id, name]` / `false`), `OdxVariant<T>`
  (value or `false`). Use them in your models.
- Failures complete the future exceptionally: `OdxServerErrorException` for
  envelopes/HTTP errors, `IOException` for transport/serialization.

## PHP — `odxproxy/client`

Zero-dependency (ext-curl, ext-json), synchronous.

```php
use OdxProxy\Odx;

Odx::init([
    'gateway_url' => 'https://proxy.example.com', 'gateway_api_key' => '<proxy x-api-key>',
    'url' => 'https://erp.example.com', 'db' => 'prod', 'user_id' => 2, 'api_key' => '<odoo key>',
    'context' => ['lang' => 'en_US', 'allowed_company_ids' => [1]],   // optional, v2 only
]);

// v1 — the SDK wraps the domain for you; options via KeywordRequest
$rows = Odx::searchRead('res.partner', [['is_company', '=', true]]);
Odx::call('sale.order', 'action_confirm', [[100]]);        // call_method is `call`

// v2 — named PHP args
$v2   = Odx::v2();                                         // or Odx::with($cfg)->v2() per tenant
$rows = $v2->searchRead('res.partner', [['is_company', '=', true]], fields: ['name'], limit: 20);
$ids  = $v2->create('res.partner', [['name' => 'Acme']]);  // [42]
$v2->call('account.move', 'action_post', ids: [7]);
$v2->call('res.partner', 'name_search', ['name' => 'Acm', 'limit' => 5]);
```

- Multi-tenant: `Odx::with($config)` builds a throwaway client without touching
  the global one; never call `Odx::init()` in a loop.
- `user_id` is only needed for v1 methods.
- v1 `OdxException::getCode()` holds the HTTP status on non-2xx; use
  `rpcCode()` for the JSON-RPC code. Don't compare `getCode()` with `0`.

## Swift — `ODXProxyClientSwift`

`async throws`, singleton, iOS 15+/macOS 12+/tvOS/watchOS/visionOS, Swift 6.2+.
Decoding and I/O run off the main actor.

```swift
OdxProxyClient.shared.configure(with: OdxProxyClientInfo(
    instance: OdxInstanceInfo(url: "https://erp.example.com", userId: 2, db: "prod", apiKey: "<odoo key>"),
    odxApiKey: "<proxy x-api-key>",
    gatewayUrl: "https://proxy.example.com",
    defaultContext: OdxContext(lang: "en_US", allowedCompanyIds: [1])))      // optional, v2 only

// v1 — wrapped domain in OdxParams; annotate the generic result type
let r1: OdxServerResponse<[Partner]> = try await OdxApi.searchRead(model: "res.partner",
    params: OdxParams([[["is_company", "=", true]]]),
    keyword: OdxClientKeywordRequest(fields: ["id", "name"], limit: 20,
                                     context: OdxClientRequestContext(tz: "UTC")))   // context is required

// v2
let r2: OdxServerResponse<[Partner]> = try await OdxApiV2.searchRead(model: "res.partner",
    domain: OdxParams([["is_company", "=", true]]), fields: ["name"], limit: 20)
let ids = try await OdxApiV2.create(model: "res.partner", values: [OdxParams(["name": "Acme"])])   // [42]
let _: OdxServerResponse<Bool> = try await OdxApiV2.callMethod(model: "account.move", method: "action_post", ids: [7])
```

- `unlink` is **`remove`**; v1 `callMethod(functionName:)`.
- Generic results must be annotated at the call site, or it won't compile.
- `OdxParams([])` doesn't compile for v1 — use `OdxParams([[]] as [[Any]])`.
- Odoo-quirk helpers: `OdxMany2One`, `@OdxOptional var x: T?` (`false` → `nil`).
- Ops: `OdxOps.about()`, `OdxOps.license()`.

## .NET / C# — `TerraKernel.OdxClient`

A Rust C-ABI core (`odxclient.dll`, **win-x64 only**) behind a thin,
Native-AOT-friendly binding; .NET 10; **async only** (never `.Result`/`.Wait()`).
The NuGet page lists computed targets like `net10.0-android`/`-ios`/`-macos` —
they don't work; there is no native core for them. For macOS/Linux/mobile, use
another SDK or the raw contract.

```csharp
using var client = OdxClient.Create(baseUrl: "https://proxy.example.com", apiKey: "<proxy x-api-key>");

// v1 — one ExecuteAsync + OdxAction enum; params/keyword are raw JSON bytes
var odoo = new OdooInstance { Url = "https://erp.example.com", Db = "prod", UserId = 2, ApiKey = "<odoo key>" };
Partner[]? a = await client.ExecuteAsync(OdxAction.SearchRead, "res.partner", odoo,
    AppJson.Default.PartnerArray,
    paramsJson: """[[["is_company","=",true]]]"""u8.ToArray(),
    keywordJson: """{"fields":["name"],"limit":20}"""u8.ToArray());

// v2 — a session with per-method calls; JSON args are OdxJson (JsonNode or UTF-8 bytes)
OdxSessionV2 erp = client.ForInstanceV2(url: "https://erp.example.com", db: "prod", apiKey: "<odoo key>",
    context: new JsonObject { ["lang"] = "en_US" });
Partner[]? b = await erp.SearchReadAsync("res.partner", AppJson.Default.PartnerArray,
    domain: OdxJson.Parse("""[["is_company","=",true]]"""), fields: ["name"], limit: 20);
long[] ids = await erp.CreateAsync("res.partner", OdxJson.Parse("""[{"name":"Acme"}]"""));   // [42]
await erp.CallMethodAsync("account.move", "action_post", AppJson.Default.JsonElement, ids: [7]);
```

- Typed calls need a source-generated `JsonTypeInfo<T>` from your
  `JsonSerializerContext` (reflection-free, AOT-safe).
- `OdxAction.CallMethod` requires `fnName:` (checked client-side).
  `ForInstanceV2(odoo)` reuses a v1 `OdooInstance` (its `UserId` is ignored).
- Opt-in converters in `TerraKernel.OdxClient.Json`: `Many2One`,
  `OdooFalseAsNullStringConverter`, `OdooBinary` (Odoo 20 `{content, filename, size}`).
- Cancellation (`CancellationToken`) surfaces `OperationCanceledException`.

---

## When advising on a language

1. Read that SDK's README/source at the user's installed version (repo URLs
   above). Check whether it is new enough for v2 (table above) if v2 is needed.
2. Keep that SDK's own naming (`remove` vs `unlink`, `call` vs `call_method`,
   snake vs camel) — but the JSON keys on the wire never change.
3. Mind the v1 domain wrapping: Python, JS, Java, Swift and .NET take v1
   `params` as execute_kw's positional args, so the domain is wrapped
   (`[[...]]`); only PHP takes the bare domain and wraps it itself. In v2 every
   SDK takes the bare domain. (A bare domain passed as v1 `params` fails in Odoo
   with `ValueError: Domain() invalid item`; some README examples get this wrong.)
4. If no SDK fits (Dart, Go, Rust, Linux .NET, multi-tenant on a singleton
   SDK…), implement the raw contract in `api-reference.md` — it's stable
   regardless of SDK drift.
