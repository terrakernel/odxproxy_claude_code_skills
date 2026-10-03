# Actions (v1) and Methods (v2)

Authoritative source: https://odxproxy.io/docs/actions and the proxy repo's
`SYSTEM_ARCHITECTURE.md` §5 and §7.1. v1 and v2 reach the same Odoo methods but
shape the arguments differently — don't mix the two shapes.

A "domain" is an Odoo search domain: a list of `[field, operator, value]`
triples (with optional `"&"`, `"|"`, `"!"` logical prefixes), e.g.
`[["is_company", "=", true], ["country_id.code", "=", "SG"]]`.

---

## v1: the 9 allowed actions

The `action` value must match one of these exactly; anything else → HTTP 400 /
JSON-RPC `-32001`. Each maps to an Odoo `execute_kw` method. `params` is the
positional `args` list; `keyword` is the `kwargs` object. The exact shape of
`params` follows Odoo's own method signature.

| Action | Odoo method | Purpose |
|--------|-------------|---------|
| `search_count` | `search_count` | Count records matching a domain |
| `search` | `search` | Return record IDs matching a domain |
| `read` | `read` | Read fields for given IDs |
| `fields_get` | `fields_get` | Describe a model's fields |
| `search_read` | `search_read` | Search + read in one call |
| `create` | `create` | Create record(s) |
| `write` | `write` | Update record(s) by ID |
| `unlink` | `unlink` | Delete record(s) by ID |
| `call_method` | *(named by `fn_name`)* | Invoke an arbitrary model method |

`model_id` is always the Odoo model name. Below, `params` is shown as the JSON
array and `keyword` as the JSON object. Note the domain is **wrapped** in the
positional list: `params: [domain]`.

### search_count
```json
{ "action": "search_count", "model_id": "res.partner",
  "params": [[["is_company", "=", true]]] }
```
`params[0]` = domain. Returns an integer.

### search
```json
{ "action": "search", "model_id": "res.partner",
  "params": [[["is_company", "=", true]]],
  "keyword": { "limit": 50, "offset": 0, "order": "name asc" } }
```
`params[0]` = domain. Returns an array of ids.

### read
```json
{ "action": "read", "model_id": "res.partner",
  "params": [[1, 2, 3], ["name", "email"]] }
```
`params[0]` = list of ids, `params[1]` = list of fields (optional; omit for all).
Returns an array of record dicts.

### fields_get
```json
{ "action": "fields_get", "model_id": "res.partner",
  "keyword": { "attributes": ["string", "type", "required", "relation", "selection"] } }
```
Returns a dict keyed by field name describing each field. See
`odoo-introspection.md` for how to use this to map a model.

### search_read
```json
{ "action": "search_read", "model_id": "res.partner",
  "params": [[["is_company", "=", true]]],
  "keyword": { "fields": ["id", "name", "email"], "limit": 50, "offset": 0, "order": "name asc" } }
```
`params[0]` = domain. Returns an array of record dicts. Preferred over
`search` + `read` for most reads.

### create
```json
{ "action": "create", "model_id": "res.partner",
  "params": [{ "name": "Acme Inc", "is_company": true }] }
```
`params[0]` = values dict → returns the new id (an integer). A list of dicts →
returns a list of ids.

### write
```json
{ "action": "write", "model_id": "res.partner",
  "params": [[42], { "name": "Acme LLC" }] }
```
`params[0]` = list of ids, `params[1]` = values dict. Returns `true`.

### unlink
```json
{ "action": "unlink", "model_id": "res.partner",
  "params": [[42]] }
```
`params[0]` = list of ids. Returns `true`.

### call_method
```json
{ "action": "call_method", "model_id": "sale.order", "fn_name": "action_confirm",
  "params": [[42]] }
```
`fn_name` is **required** and must be non-empty (empty → HTTP 400 / `-32002`;
SDKs also raise client-side). `params` matches the target method's signature.
Use this for workflow/business methods beyond CRUD (e.g. confirming an order,
posting an invoice). This is the escape hatch, but it can invoke anything the
Odoo user is permitted to — prefer the specific CRUD actions when they suffice.

---

## v2: methods and the `kwargs` they send

Every v2 call is `POST /v2/odoo/execute` with `model_id`, `method` and one
`kwargs` **object**. There is no allowlist, no `action`, no `fn_name`, and no
positional arguments. JSON-2 checks every key against the method's Python
signature: an unknown, misspelled or missing name is Odoo error `422`.

| Operation | `method` | `kwargs` keys (exact) | Result |
|---|---|---|---|
| search + read | `search_read` | `domain`, `fields`, `offset`, `limit`, `order` | array of objects |
| search | `search` | `domain`, `offset`, `limit`, `order` | array of ids |
| count | `search_count` | `domain`, `limit` | integer |
| read | `read` | `ids`, `fields`, `load` | array of objects |
| schema | `fields_get` | `allfields`, `attributes` | object keyed by field name |
| create | `create` | `vals_list` — **always an array** | **array of ids, always** |
| update | `write` | `ids`, `vals` | `true` |
| delete | `unlink` | `ids` | `true` |
| anything else | *the method name* | `ids` (record methods only) + the method's named args | the method's return value; a recordset becomes an array of ids |

Every call may also carry `context` (`lang`, `tz`, `allowed_company_ids`, …).

```json
{ "model_id": "res.partner", "method": "search_read",
  "kwargs": { "domain": [["is_company", "=", true]], "fields": ["name"], "limit": 50 } }

{ "model_id": "res.partner", "method": "create",
  "kwargs": { "vals_list": [{ "name": "Acme" }] } }                  // → [42]

{ "model_id": "res.partner", "method": "write",
  "kwargs": { "ids": [42], "vals": { "name": "Acme LLC" } } }

{ "model_id": "sale.order", "method": "action_confirm",
  "kwargs": { "ids": [42] } }                                        // record method

{ "model_id": "res.partner", "method": "name_search",
  "kwargs": { "name": "Acm", "limit": 5 } }                          // @api.model method
```

Rules:

- **Wire keys are Odoo's Python names, verbatim.** Never camelCase them
  (`vals_list`, not `valsList`; `allfields`, not `allFields`), and never
  transform keys inside `vals`, `domain` or `context` — those are Odoo field
  names. An SDK may expose idiomatic argument names, but the JSON must not change.
- **The domain is the list itself:** `"domain": [["a","=",1]]`. v1's extra
  wrapping list is gone. An empty domain is `[]`.
- **Omit unset arguments** instead of sending `null`, so Odoo's own defaults
  apply (`null` means Python `None`).
- **`ids` only for record methods.** Sending `ids` to an `@api.model` method
  (`search`, `search_read`, `search_count`, `fields_get`, `create`,
  `name_search`, …) is a `422`.
- **Finding parameter names** for other methods: the method's Python definition,
  or `/doc/<model>` in the Odoo 19+ web UI.
- **`create`:** wrap a single dict in a list; expect a list back. v1 differs here
  (a single dict there returns a bare integer).

---

## Relational field writes (x2many) — both versions

For one2many/many2many fields, Odoo uses command tuples inside the values dict,
e.g. `[[6, 0, [ids]]]` to replace, `[[4, id]]` to link, `[[0, 0, {vals}]]` to
create-and-link. These pass through `create`/`write` unchanged (v1 `params`, v2
`vals`/`vals_list`) — confirm the target field's `type` via `fields_get` first.
