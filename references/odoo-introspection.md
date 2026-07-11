# Understanding a Target Odoo Instance

Odoo models are heavily customized per deployment: custom fields, renamed
selections, extra models, module-specific behavior. **Never assume field names.**
Discover the real schema through the proxy before writing application code.

Use any SDK's built-in `fields_get` method (every official SDK ships one) or
`scripts/odx.py` (zero-dependency CLI) to run the calls below. **`fields_get`
comes first, before you define any native-language struct/class/DTO** — the
schema it returns is what you serialize into; don't hand-write the model shape
from assumptions.

## Discovery recipe

### 1. Confirm connectivity and version
```
python scripts/odx.py version
```
Then a cheap sanity read: `search_count` on `res.partner`.

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
  `date`, `datetime`, `binary`.
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

### 6. Find the right model
If unsure which model holds something, introspect Odoo's own metadata models:
- `ir.model` — `search_read` with fields `model`, `name` to list/search models.
- `ir.model.fields` — fields across models (filter by `model_id` or `name`).

## Output an agent should produce

After introspection, summarize for the user before coding:
- The target model(s) and the exact fields the app will read/write.
- Field types + which are `required` on create.
- Selection value sets and relation targets.
- Any field whose existence/meaning still needs user confirmation.

This turns "understand the data structure" into a concrete contract the
application code is written against.
