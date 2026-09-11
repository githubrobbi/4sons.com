#!/usr/bin/env python3
"""Family email lock for the Nio family web sites, via Cloudflare Access (Zero Trust).

Idempotent: run it as often as you like. It makes sure that
  1. the account has a Zero Trust organization (team name -> <team>.cloudflareaccess.com),
  2. the One-time PIN login method exists,
  3. a service token exists for the front-door Worker (secret stored in gopass),
  4. two Access applications exist: the section paths on the zone, and the direct
     *.pages.dev origins (family Allow policy + the Worker's service token).

Token: gopass 4sons/cloudflare/api-token/access (custom token, account-scoped) with
  Access: Apps and Policies: Edit
  Access: Organizations, Identity Providers, and Groups: Edit
  Zero Trust: Edit
Account id: gopass 4sons/cloudflare/account-id

Usage:
  scripts/cf_access_family.py            # apply for the 4 Sons account
  scripts/cf_access_family.py --dry-run  # show what would change
  scripts/cf_access_family.py --account-path personal/cloudflare/nios --config nios   # later, nios.net
"""
import argparse, json, subprocess, sys, urllib.request, urllib.error

API = "https://api.cloudflare.com/client/v4"

# The lock definition. Landing pages and David's site (the Sky, LLC identity site) stay public.
# "zone" destinations are paths on the account's own zone; "pages" are the direct *.pages.dev
# origins of the sections (only projects that exist can be listed, so they are filtered at run time).
# The front-door Worker fetches those origins with a service token, so the lock on the origin
# does not break the proxy.
CONFIGS = {
    "4sons": {
        "team": "4sons",
        "service_token": "4sons-front-door",
        "zone_app": {"name": "4 Sons family sections", "session": "720h",
                     "destinations": ["4sons.com/joni", "4sons.com/benji", "4sons.com/sami"]},
        "pages_app": {"name": "4 Sons family Pages origins", "session": "720h",
                      "projects": ["4sons-joni-site", "4sons-benji-site", "4sons-sami-site"]},
    },
    "nios": {
        "team": "nios",
        "service_token": "nios-front-door",
        "zone_app": {"name": "nios.net family sections", "session": "720h",
                     "destinations": ["nios.net/robert", "nios.net/esther", "nios.net/familie"]},
        "pages_app": {"name": "nios.net family Pages origins", "session": "720h",
                      "projects": ["nios-robert", "nios-esther", "nios-familie"]},
    },
}

# Who may open the pages. Domain rule covers every @nios.net alias; add personal
# addresses here when a family member reads mail somewhere else.
FAMILY_EMAIL_DOMAINS = ["nios.net"]
FAMILY_EMAILS = ["nfbmailbox@gmail.com"]


def gopass(path):
    return subprocess.check_output(["gopass", "show", "-o", path]).decode().strip()


class CF:
    def __init__(self, token, account):
        self.token, self.account = token, account

    def call(self, method, path, body=None):
        req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:
            d = json.load(e)
        if not d.get("success"):
            raise SystemExit(f"{method} {path} failed: {d.get('errors')}")
        return d.get("result")

    def acct(self, method, path, body=None):
        return self.call(method, f"/accounts/{self.account}{path}", body)


def ensure_org(cf, team, dry):
    try:
        org = cf.acct("GET", "/access/organizations")
    except SystemExit as e:
        org = None
        print("  organizations GET:", e)
    if org and org.get("auth_domain"):
        print(f"  org ok: {org['auth_domain']}")
        return
    print(f"  creating Zero Trust org {team}.cloudflareaccess.com")
    if not dry:
        cf.acct("POST", "/access/organizations", {"name": "The Nio Family", "auth_domain": f"{team}.cloudflareaccess.com",
                                                   "is_ui_read_only": False, "auto_redirect_to_identity": False})


def ensure_otp(cf, dry):
    idps = cf.acct("GET", "/access/identity_providers") or []
    if any(i.get("type") == "onetimepin" for i in idps):
        print("  one-time PIN login ok")
        return
    print("  adding one-time PIN login")
    if not dry:
        cf.acct("POST", "/access/identity_providers", {"name": "One-time PIN", "type": "onetimepin", "config": {}})


def policy_include():
    inc = [{"email_domain": {"domain": d}} for d in FAMILY_EMAIL_DOMAINS]
    inc += [{"email": {"email": e}} for e in FAMILY_EMAILS]
    return inc


def ensure_service_token(cf, name, account_path, dry):
    """The front-door Worker presents this token when it fetches a locked Pages origin.
    The secret is only ever returned at creation; it goes straight into gopass, never on screen."""
    toks = cf.acct("GET", "/access/service_tokens") or []
    t = next((t for t in toks if t.get("name") == name), None)
    if t:
        print(f"  service token '{name}' ok ({t['id']})")
        return t["id"]
    print(f"  creating service token '{name}' (secret -> gopass {account_path}/access-service-token/{name}/secret)")
    if dry:
        return None
    t = cf.acct("POST", "/access/service_tokens", {"name": name, "duration": "8760h"})
    for k, v in (("client-id", t["client_id"]), ("secret", t["client_secret"])):
        subprocess.run(["gopass", "insert", "-f", f"{account_path}/access-service-token/{name}/{k}"], input=v.encode(), check=True)
    return t["id"]


def app_body(name, session, destinations, policies):
    return {
        "name": name, "type": "self_hosted", "domain": destinations[0],
        "destinations": [{"type": "public", "uri": d} for d in destinations],
        "session_duration": session, "allowed_idps": [], "auto_redirect_to_identity": False,
        "app_launcher_visible": False, "http_only_cookie_attribute": True, "policies": policies,
    }


def family_policy(precedence=1):
    return {"name": "Family", "decision": "allow", "precedence": precedence,
            "include": policy_include(), "exclude": [], "require": []}


def upsert_app(cf, body, dry):
    apps = cf.acct("GET", "/access/apps") or []
    existing = next((a for a in apps if a.get("name") == body["name"]), None)
    dests = ", ".join(d["uri"] for d in body["destinations"])
    if existing:
        print(f"  updating app '{body['name']}': {dests}")
        if not dry:
            cf.acct("PUT", f"/access/apps/{existing['id']}", body)
    else:
        print(f"  creating app '{body['name']}': {dests}")
        if not dry:
            cf.acct("POST", "/access/apps", body)


def ensure_apps(cf, cfg, token_id, account_path, dry):
    z = cfg["zone_app"]
    upsert_app(cf, app_body(z["name"], z["session"], z["destinations"], [family_policy()]), dry)
    p = cfg["pages_app"]
    # Pages listing needs a token with Pages read; the wrangler token has it, the Access token does not.
    try:
        pages_cf = CF(gopass(f"{account_path}/api-token/wrangler"), cf.account)
    except subprocess.CalledProcessError:
        pages_cf = cf
    existing_projects = {x["name"] for x in (pages_cf.acct("GET", "/pages/projects") or [])}
    projects = [x for x in p["projects"] if x in existing_projects]
    missing = [x for x in p["projects"] if x not in existing_projects]
    if missing:
        print(f"  (Pages projects not created yet, skipped: {', '.join(missing)})")
    if not projects:
        print("  no Pages origins to lock yet")
        return
    dests = []
    for x in projects:
        dests += [f"{x}.pages.dev", f"*.{x}.pages.dev"]
    policies = [family_policy(1)]
    if token_id:
        policies.append({"name": "Front-door Worker", "decision": "non_identity", "precedence": 2,
                         "include": [{"service_token": {"token_id": token_id}}], "exclude": [], "require": []})
    upsert_app(cf, app_body(p["name"], p["session"], dests, policies), dry)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="4sons", choices=CONFIGS)
    ap.add_argument("--account-path", default="4sons/cloudflare", help="gopass folder holding account-id and api-token/access")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cf = CF(gopass(f"{a.account_path}/api-token/access"), gopass(f"{a.account_path}/account-id"))
    cfg = CONFIGS[a.config]
    print(f"account {cf.account} · config {a.config}{' · DRY RUN' if a.dry_run else ''}")
    ensure_org(cf, cfg["team"], a.dry_run)
    ensure_otp(cf, a.dry_run)
    token_id = ensure_service_token(cf, cfg["service_token"], a.account_path, a.dry_run)
    ensure_apps(cf, cfg, token_id, a.account_path, a.dry_run)
    print("done" if not a.dry_run else "dry run complete")


if __name__ == "__main__":
    main()
