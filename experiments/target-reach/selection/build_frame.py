"""Build the selection frame: the 1,000 most-downloaded PyPI projects of the
snapshot, each with its PyPI metadata, and the keyword filter that names the
candidates. Mechanical; no package is installed or run."""
import concurrent.futures, hashlib, json, re, sys, urllib.request

TOP = 1000
KEYWORDS = (r"jwt|jose|jws|jwk|paseto|macaroon|signature|signing|signed|verif|token|oauth|openid|oidc|saml|"
            r"webauthn|fido|dnssec|x\.?509|certificate|pki|tls|ssl|ssh|crypt|hmac|otp|kerberos|ntlm|attest|"
            r"sigstore|in-toto|notary|pgp|gpg|dkim|auth")

def fetch(name):
    req = urllib.request.Request(f"https://pypi.org/pypi/{name}/json", headers={"User-Agent": "frame-builder/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            info = json.load(r)["info"]
    except Exception as e:  # recorded, not hidden
        return name, {"error": repr(e)}
    return name, {k: info.get(k) for k in ("version", "summary", "keywords", "license", "home_page", "project_urls", "requires_python")}

def main():
    snap = json.load(open("top-pypi-packages.min.json"))
    rows = snap["rows"][:TOP]
    names = [r["project"] for r in rows]
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        meta = dict(ex.map(fetch, names))
    out = []
    for rank, r in enumerate(rows, 1):
        m = meta[r["project"]]
        text = " ".join([r["project"], m.get("summary") or "", m.get("keywords") or ""]).lower()
        hit = sorted(set(re.findall(KEYWORDS, text)))
        out.append({"rank": rank, "project": r["project"], "downloads_30d": r["download_count"], **m, "keyword_hits": hit})
    json.dump({"snapshot_last_update": snap["last_update"], "snapshot_sha256": hashlib.sha256(open("top-pypi-packages.min.json","rb").read()).hexdigest(),
               "top": TOP, "keywords": KEYWORDS, "rows": out}, open("frame-top1000.json", "w"), indent=1, ensure_ascii=False)
    cands = [o for o in out if o["keyword_hits"]]
    print(len(out), "projects;", sum(1 for o in out if "error" in o), "metadata errors;", len(cands), "candidates")
    for o in cands:
        print(o["rank"], o["project"], "|", (o.get("summary") or "")[:90], "|", ",".join(o["keyword_hits"]))

main()
