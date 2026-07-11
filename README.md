# ODXProxy — Claude Code Skills

A collection of [Claude Code](https://claude.com/claude-code) **skills** for
working with [ODXProxy](https://odxproxy.io), the Rust JSON-RPC proxy that fronts
Odoo ERP.

## Skills in this repo

| Skill | Folder | What it does |
|-------|--------|--------------|
| `odxproxy-clients` | [`odxproxy-clients/`](./odxproxy-clients) | Build apps against Odoo through ODXProxy — introspect the target Odoo's data model, then generate a client on an official SDK (Python, Java, PHP, Kotlin, Swift, JS/TS) or the raw JSON-RPC contract. |

More skills may be added as sibling folders over time — each is a self-contained
directory with its own `SKILL.md`.

## Install

Claude Code discovers skills as direct subfolders of a `skills/` directory
(`~/.claude/skills/<name>/SKILL.md` for personal, `<project>/.claude/skills/…`
for a project). Because this repo bundles skills in subfolders, install links
each skill into place with the included script.

### Personal (all your projects)

```bash
git clone https://github.com/terrakernel/odxproxy_claude_code_skills.git
cd odxproxy_claude_code_skills
./install.sh
```

`install.sh` symlinks every skill folder into `~/.claude/skills/`, so a later
`git pull` in this repo updates the installed skills automatically. Re-run it
after pulling if new skills were added. Pass `--copy` to copy instead of symlink,
or a target dir as the first argument (e.g. `./install.sh .claude/skills` inside
a project to scope the skills to that repo).

### Manual / project-scoped

Copy or symlink the individual skill folder yourself:

```bash
ln -s "$(pwd)/odxproxy-clients" ~/.claude/skills/odxproxy-clients
# or, project-scoped:
cp -R odxproxy-clients /path/to/project/.claude/skills/odxproxy-clients
```

After installing, start a new Claude Code session so the skills are picked up.
See each skill's own `README.md` for usage details.

## License

MIT © Terrakernel Pte. Ltd. — see [`LICENSE`](./LICENSE).
