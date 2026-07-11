# The 9 Allowed Actions

Authoritative source: https://odxproxy.io/docs/actions . The `action` value must
match one of these exactly; anything else → HTTP 400 / JSON-RPC `-32001`.

Each action maps to an Odoo `execute_kw` method. `params` is the positional
`args` list; `keyword` is the `kwargs` object. The exact shape of `params`
follows Odoo's own method signature.

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

A "domain" is an Odoo search domain: a list of `[field, operator, value]`
triples (with optional `"&"`, `"|"`, `"!"` logical prefixes), e.g.
`[["is_company", "=", true], ["country_id.code", "=", "SG"]]`.

## Per-action shapes

`model_id` is always the Odoo model name. Below, `params` is shown as the JSON
array and `keyword` as the JSON object.

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
`params[0]` = values dict (or, on Odoo versions that support it, a list of
dicts). Returns the new id (or list of ids).

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

## Relational field writes (x2many)

For one2many/many2many fields, Odoo uses command tuples inside the values dict,
e.g. `[[6, 0, [ids]]]` to replace, `[[4, id]]` to link, `[[0, 0, {vals}]]` to
create-and-link. These pass through `create`/`write` unchanged — confirm the
target field's `type` via `fields_get` first.
