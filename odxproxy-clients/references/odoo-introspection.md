# Understanding a Target Odoo Instance

Odoo models are heavily customized per deployment: custom fields, renamed
selections, extra models, module-specific behavior. **Never assume field names.**
Discover the real schema through the proxy before writing application code.

Use the SDK's built-in `fields_get` (a method in every SDK, v1 and v2) or
`scripts/odx.py` (zero-dependency CLI) to run the calls below. Every `odx.py`
command works on both API versions: add `--v2` for Odoo 19+ (required on 22+),
e.g. `python scripts/odx.py --v2 fields_get res.partner`. **`fields_get`
comes first, before you define any native-language struct/class/DTO** — the
schema it returns is what you serialize into; don't hand-write the model shape
from assumptions.

## Discovery recipe

### 1. Confirm connectivity and version — and pick v1 or v2
```
python scripts/odx.py version          # v1: server_version, server_version_info
python scripts/odx.py --v2 version     # v2: {"version_info": [20, 0, ...], "version": "20.0+e"}
```
Major ≥ 19 → v2 is available (and is the only option from 22). `--v2 version`
failing with `-32006` → Odoo ≤18, use v1. Then a cheap sanity read:
`search_count` on `res.partner` with the chosen version. If `--v2 version`
works but `--v2 search_count` fails with `-32006`, the database isn't
selectable on that host (`dbfilter`) — see `api-reference.md`.

### 2. Describe a model's fields (`fields_get`)
```
python scripts/odx.py fields_get res.partner
```
For each field you get `string` (label), `type`, `required`, `readonly`,
`relation` (target model for relational fields), `selection` (for selection
fields), and `help`. This is the single most useful call — it is the model's
schema. Narrow noise with `keyword.attributes`:
`{"attributes": ["string","type","required","relation","selection"]}`.

### 3. Classify the fields
- **Scalars:** `char`, `text`, `integer`, `float`, `monetary`, `boolean`,
  `date`, `datetime` (UTC strings `"YYYY-MM-DD HH:MM:SS"`), `html`.
- **binary:** a bare base64 string on Odoo ≤19, but on **Odoo 20+** (v1 and v2
  alike) an object `{"content": "<base64>", "filename": ..., "size": n}`. Model
  it per the target's version; on write, a base64 string or
  `{"filename", "content"}` is accepted.
- **Empty values are `false`, not `null`** — for strings, dates, many2one, etc.
  Native models must tolerate `false` in any non-boolean field.
- **Selection:** has a `selection` list of `[value, label]` — the only valid
  write values are those `value`s.
- **many2one:** stored as `[id, display_name]` on read; write an integer id.
  Follow `relation` to the target model.
- **one2many / many2many:** lists of ids on read; write via command tuples
  (`[[6,0,[ids]]]`, `[[4,id]]`, `[[0,0,{vals}]]` — see `actions.md`).

### 4. Follow relations to build the model graph
For every `many2one`/`x2many`, note its `relation` and (if relevant) run
`fields_get` on that target too. This yields the graph you'll traverse in the
app (e.g. `sale.order` → `order_line` → `sale.order.line` → `product_id` →
`product.product`).

### 5. Sample real records (`search_read`)
```
python scripts/odx.py search_read res.partner --fields name,email,country_id --limit 5
```
Sampling shows actual value shapes (e.g. many2one as `[id, "name"]`), which
selection values are really used, and whether fields are populated in practice.

### 6. Find the right model (and method parameters)
On Odoo 19+, `/doc/<model>` in the web UI lists a model's
fields and public methods with their Python parameter names — exactly the keys
v2 `kwargs` need. If unsure which model holds something, introspect Odoo's own
metadata models:
- `ir.model` — `search_read` with fields `model`, `name` to list/search models.
- `ir.model.fields` — fields across models (filter by `model_id` or `name`).

## Output an agent should produce

After introspection, summarize for the user before coding:
- The target model(s) and the exact fields the app will read/write.
- Field types + which are `required` on create.
- Selection value sets and relation targets.
- Any field whose existence/meaning still needs user confirmation.
- The API version the app will use (v1 or v2) and why (Odoo version, upgrade
  plans).

This turns "understand the data structure" into a concrete contract the
application code is written against.
