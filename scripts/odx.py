#!/usr/bin/env python3
"""
odx.py — a zero-dependency CLI for calling an ODXProxy instance.

Purpose: let an agent (or a human) introspect a target Odoo instance and test
calls against the proxy without installing any SDK. Uses only the Python stdlib.

Configuration comes from environment variables (or a --env-file / .env):
  ODX_PROXY_URL     proxy base URL, e.g. https://proxy.example.com
  ODX_PROXY_KEY     the PROXY api key (sent as the x-api-key header)
  ODX_ODOO_URL      target Odoo base URL
  ODX_ODOO_DB       Odoo database name
  ODX_ODOO_USER_ID  Odoo user id (integer)
  ODX_ODOO_API_KEY  the ODOO USER api key

The two keys are different: ODX_PROXY_KEY authenticates you to the proxy;
ODX_ODOO_API_KEY authenticates the proxy to Odoo. See references/api-reference.md.

Examples:
  python odx.py version
  python odx.py search_count res.partner --domain '[["is_company","=",true]]'
  python odx.py search_read res.partner --fields name,email --limit 5
  python odx.py fields_get res.partner --attrs string,type,required,relation,selection
  python odx.py read res.partner --ids 1,2,3 --fields name,email
  python odx.py create res.partner --values '{"name":"Acme","is_company":true}'
  python odx.py write res.partner --ids 42 --values '{"name":"Acme LLC"}'
  python odx.py unlink res.partner --ids 42
  python odx.py call_method sale.order action_confirm --params '[[42]]'
  python odx.py execute --action search --model res.partner --params '[[["id",">",0]]]'

Every response is checked for the 200-with-error case; a proxy or Odoo error
exits non-zero with the JSON-RPC error printed to stderr.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid


class OdxError(Exception):
    def __init__(self, code, message, data=None, http_status=None, request_id=None):
        self.code = code
        self.message = message
        self.data = data
        self.http_status = http_status
        self.request_id = request_id
        super().__init__(f"[{code}] {message}")


def load_env_file(path):
    if not path or not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def require_env(*names):
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        sys.exit(f"error: missing required env var(s): {', '.join(missing)}")
    return [os.environ[n] for n in names]


def odoo_instance():
    url, db, uid, key = require_env(
        "ODX_ODOO_URL", "ODX_ODOO_DB", "ODX_ODOO_USER_ID", "ODX_ODOO_API_KEY"
    )
    try:
        uid = int(uid)
    except ValueError:
        sys.exit("error: ODX_ODOO_USER_ID must be an integer")
    return {"url": url, "db": db, "user_id": uid, "api_key": key}


def post(path, body, timeout_secs=None):
    proxy_url, proxy_key = require_env("ODX_PROXY_URL", "ODX_PROXY_KEY")
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "x-api-key": proxy_key}
    if timeout_secs:
        headers["x-request-timeout"] = str(int(timeout_secs))
    req = urllib.request.Request(
        proxy_url.rstrip("/") + path, data=data, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=(timeout_secs or 45) + 5) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:  # non-2xx
        status = e.code
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            raise OdxError(status, f"HTTP {status}", raw, http_status=status)
    except urllib.error.URLError as e:
        raise OdxError(599, f"Network error: {e.reason}")

    # Two-step success check: an error can ride on any status, including 200.
    err = payload.get("error") if isinstance(payload, dict) else None
    if err:
        raise OdxError(
            err.get("code"), err.get("message", ""), err.get("data"),
            http_status=status, request_id=payload.get("id"),
        )
    if status != 200:
        raise OdxError(status, f"HTTP {status} without error object", payload,
                       http_status=status)
    return payload.get("result")


def execute(action, model, params=None, keyword=None, fn_name=None, timeout=None):
    body = {
        "id": str(uuid.uuid4()),
        "action": action,
        "model_id": model,
        "params": params if params is not None else [],
        "keyword": keyword if keyword is not None else {},
        "odoo_instance": odoo_instance(),
    }
    if fn_name is not None:
        body["fn_name"] = fn_name
    return post("/api/odoo/execute", body, timeout_secs=timeout)


def _json(arg, default):
    if arg is None:
        return default
    return json.loads(arg)


def _csv(arg):
    return [x.strip() for x in arg.split(",") if x.strip()] if arg else None


def _ids(arg):
    return [int(x) for x in _csv(arg)] if arg else []


def build_parser():
    p = argparse.ArgumentParser(description="Zero-dependency ODXProxy CLI.")
    p.add_argument("--env-file", help="path to a .env file to load")
    p.add_argument("--timeout", type=int, help="x-request-timeout seconds")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="GET Odoo version via /api/odoo/version")

    def add_model(sp):
        sp.add_argument("model", help="Odoo model, e.g. res.partner")

    sc = sub.add_parser("search_count"); add_model(sc)
    sc.add_argument("--domain", help='JSON domain, e.g. [["is_company","=",true]]')

    s = sub.add_parser("search"); add_model(s)
    s.add_argument("--domain"); s.add_argument("--limit", type=int)
    s.add_argument("--offset", type=int); s.add_argument("--order")

    sr = sub.add_parser("search_read"); add_model(sr)
    sr.add_argument("--domain"); sr.add_argument("--fields")
    sr.add_argument("--limit", type=int); sr.add_argument("--offset", type=int)
    sr.add_argument("--order")

    rd = sub.add_parser("read"); add_model(rd)
    rd.add_argument("--ids", required=True); rd.add_argument("--fields")

    fg = sub.add_parser("fields_get"); add_model(fg)
    fg.add_argument("--attrs", help="comma list, e.g. string,type,required,relation")

    cr = sub.add_parser("create"); add_model(cr)
    cr.add_argument("--values", required=True, help="JSON values dict")

    wr = sub.add_parser("write"); add_model(wr)
    wr.add_argument("--ids", required=True); wr.add_argument("--values", required=True)

    ul = sub.add_parser("unlink"); add_model(ul)
    ul.add_argument("--ids", required=True)

    cm = sub.add_parser("call_method"); add_model(cm)
    cm.add_argument("fn_name"); cm.add_argument("--params")

    ex = sub.add_parser("execute", help="raw execute with explicit action")
    ex.add_argument("--action", required=True); ex.add_argument("--model", required=True)
    ex.add_argument("--params"); ex.add_argument("--keyword"); ex.add_argument("--fn-name")
    return p


def run(args):
    if args.cmd == "version":
        url, = require_env("ODX_ODOO_URL")
        return post("/api/odoo/version", {"id": str(uuid.uuid4()), "url": url})

    if args.cmd == "search_count":
        return execute("search_count", args.model,
                       params=[_json(args.domain, [])], timeout=args.timeout)

    if args.cmd == "search":
        kw = {}
        if args.limit is not None: kw["limit"] = args.limit
        if args.offset is not None: kw["offset"] = args.offset
        if args.order: kw["order"] = args.order
        return execute("search", args.model, params=[_json(args.domain, [])],
                       keyword=kw, timeout=args.timeout)

    if args.cmd == "search_read":
        kw = {}
        if args.fields: kw["fields"] = _csv(args.fields)
        if args.limit is not None: kw["limit"] = args.limit
        if args.offset is not None: kw["offset"] = args.offset
        if args.order: kw["order"] = args.order
        return execute("search_read", args.model, params=[_json(args.domain, [])],
                       keyword=kw, timeout=args.timeout)

    if args.cmd == "read":
        params = [_ids(args.ids)]
        if args.fields: params.append(_csv(args.fields))
        return execute("read", args.model, params=params, timeout=args.timeout)

    if args.cmd == "fields_get":
        kw = {"attributes": _csv(args.attrs)} if args.attrs else {}
        return execute("fields_get", args.model, keyword=kw, timeout=args.timeout)

    if args.cmd == "create":
        return execute("create", args.model, params=[_json(args.values, {})],
                       timeout=args.timeout)

    if args.cmd == "write":
        return execute("write", args.model,
                       params=[_ids(args.ids), _json(args.values, {})], timeout=args.timeout)

    if args.cmd == "unlink":
        return execute("unlink", args.model, params=[_ids(args.ids)], timeout=args.timeout)

    if args.cmd == "call_method":
        return execute("call_method", args.model, params=_json(args.params, []),
                       fn_name=args.fn_name, timeout=args.timeout)

    if args.cmd == "execute":
        return execute(args.action, args.model, params=_json(args.params, []),
                       keyword=_json(args.keyword, {}), fn_name=args.fn_name,
                       timeout=args.timeout)

    raise SystemExit(f"unknown command: {args.cmd}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    load_env_file(getattr(args, "env_file", None))
    try:
        result = run(args)
    except OdxError as e:
        detail = {"code": e.code, "message": e.message, "data": e.data,
                  "http_status": e.http_status, "request_id": e.request_id}
        print(json.dumps(detail, indent=2, default=str), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
