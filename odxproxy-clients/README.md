# ODXProxy Clients — Claude Code Skill

A [Claude Code](https://claude.com/claude-code) **skill** that makes the agent
effective at building applications against an **Odoo** ERP through
[ODXProxy](https://odxproxy.io) — the Rust JSON-RPC proxy that fronts Odoo.

It teaches Claude to:

1. **Understand a target Odoo instance's data model first** — discover fields
   and relations via `fields_get` before writing a single struct/class/DTO.
2. **Pick the right API version** — v1 (`/api/odoo/execute`, `execute_kw` over
   `/jsonrpc`, any Odoo up to 21) or v2 (`/v2/odoo/execute`, Odoo JSON-2,
   Odoo 19+ and the only option on 22+) — and use its argument shape correctly.
3. **Build the client** — either on an official ODXProxy SDK (Python,
   JavaScript/TS, Java/Kotlin, PHP, Swift, .NET/C#; all support v1 and v2) or a
   hand-rolled client against the raw JSON-RPC contract.

Official SDK packages: [`terrakernel-odxproxyclient`](https://github.com/terrakernel/ODXProxyClient-Python) (PyPI) ·
[`io.odxproxy:odxproxyclient-java`](https://github.com/terrakernel/ODXProxyClient-Java) ·
[`odxproxy/client`](https://github.com/terrakernel/ODXProxyClient-PHP) (Composer) ·
[`ODXProxyClient-Swift`](https://github.com/terrakernel/ODXProxyClient-Swift) (SwiftPM) ·
[`@terrakernel/odxproxy-client-js`](https://github.com/terrakernel/odxproxy-client-js) (npm) ·
[`TerraKernel.OdxClient`](https://www.nuget.org/packages/TerraKernel.OdxClient) (NuGet —
[repo](https://github.com/terrakernel/ODXProxyClient-Net)).

## What's in here

| Path | Purpose |
|------|---------|
| `SKILL.md` | Skill entry point (name, description, mental model, workflow). Claude loads this first. |
| `references/api-reference.md` | v1 and v2 endpoints, JSON-RPC envelope, v2 caveats (for custom clients). |
| `references/actions.md` | v1 `params`/`keyword` per action and v2 `kwargs` per method. |
| `references/errors.md` | Error-code catalog (both versions) → handling and retry strategy. |
| `references/sdks.md` | Per-language SDK packages, v1 and v2 entry points, error types, and repo URLs to refresh from. |
| `references/odoo-introspection.md` | Recipe for discovering a target Odoo's schema. |
| `scripts/odx.py` | Zero-dependency CLI over the proxy (v1 by default, `--v2` for JSON-2) for live introspection/testing. |
| `scripts/.env.example` | Config template for `odx.py` (the two distinct API keys). |
| `CLAUDE.md` | Repo-level notes for anyone editing this skill. |

Claude reads `SKILL.md` up front; the `references/` files are pulled in **only
when relevant** (progressive disclosure), so the skill stays cheap until needed.

## Installing the skill

This skill ships inside the **`odxproxy_claude_code_skills`** collection repo (in
the `odxproxy-clients/` folder). Claude Code discovers skills as direct subfolders
of a `skills/` directory, so install links this folder into place.

### Recommended — via the repo's install script

```bash
git clone https://github.com/terrakernel/odxproxy_claude_code_skills.git
cd odxproxy_claude_code_skills
./install.sh          # symlinks odxproxy-clients into ~/.claude/skills/
```

Later, `git pull` in that repo updates the installed skill automatically (it's a
symlink). See the collection [README](../README.md) for `--copy` and
project-scoped options.

### Manual / project-scoped

```bash
# personal:
ln -s "$(pwd)/odxproxy-clients" ~/.claude/skills/odxproxy-clients
# project-scoped (checked in with a repo):
cp -R odxproxy-clients /path/to/project/.claude/skills/odxproxy-clients
```

> **Naming:** the skill's identity comes from the `name:` field in `SKILL.md`
> (`odxproxy-clients`), not the folder name. Keep the installed folder named
> `odxproxy-clients` to match. After installing, start a new Claude Code session
> so the skill is picked up.

You can verify it loaded by running `/help` / checking the available skills, or
just by prompting something the description triggers on (see below).

## Using the skill

The skill **auto-triggers** — you don't have to invoke it manually. Its
`description` fires when your prompt involves ODXProxy or building an Odoo client
through it. Examples that activate it:

- "Build a Python service that reads sales orders from Odoo through ODXProxy."
- "Generate a typed TypeScript model for `res.partner` on my Odoo instance."
- "Why am I getting error -32002 from odxproxy?"
- "Introspect the `product.template` fields on my Odoo before we write the DAO."
- "We're upgrading to Odoo 20 — move our ODXProxy integration to the v2 API."

You can also point Claude at it explicitly: *"Use the odxproxy-clients skill to …"*.

## Prerequisites for the introspection script

`scripts/odx.py` needs only **Python 3** (standard library — no `pip install`).
Configure the two API keys and target instance, then run:

```bash
cp scripts/.env.example scripts/.env      # then edit the values
python3 scripts/odx.py --env-file scripts/.env fields_get res.partner
python3 scripts/odx.py --env-file scripts/.env search_read res.partner --fields name,email --limit 5

# v2 (Odoo 19+, ODXProxy 0.9.0+): same commands with --v2; ODX_ODOO_USER_ID isn't needed
python3 scripts/odx.py --env-file scripts/.env --v2 version
python3 scripts/odx.py --env-file scripts/.env --v2 fields_get res.partner --attrs type,string,relation
```

The two keys are **different**: `ODX_PROXY_KEY` authenticates you to the proxy
(`x-api-key` header); `ODX_ODOO_API_KEY` authenticates the proxy to Odoo. See
`references/api-reference.md`. The script bakes in the "HTTP 200 can still carry
an error" check, so a proxy or Odoo error exits non-zero.

## Keeping SDK knowledge fresh

The official SDKs evolve and have drifted from each other; `references/sdks.md`
records each language's real API plus its **remote git URL**. To refresh after an
SDK update, re-read the source from its repo (e.g.
`git ls-remote https://github.com/terrakernel/odxproxy-client-js` for tags, then
browse/clone) and update `sdks.md`. Treat the installed SDK's source as ground
truth over any summary here.

## License

MIT © Terrakernel Pte. Ltd. — see [`LICENSE`](./LICENSE).
ODXProxy docs: https://odxproxy.io/docs .
