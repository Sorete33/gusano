#!/usr/bin/env python3
"""One-time migration: upload existing static/nuevos covers to audiogusano-flyers/lanzamientos
and create the _lanzamientos.json sidecar from data/lanzamientos.yml."""
import base64
import json
import os
import sys
import unicodedata
import re
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import sync_github

REPO = os.environ.get("FLYERS_REPO", "Sorete33/audiogusano-flyers")
BRANCH = os.environ.get("FLYERS_BRANCH", "main")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
if not TOKEN:
    try:
        TOKEN = __import__("subprocess").check_output(["gh", "auth", "token"]).decode().strip()
    except Exception:
        pass

if not TOKEN:
    sys.exit("Set GITHUB_TOKEN/GH_TOKEN or authenticate gh.")

BASE = f"https://api.github.com/repos/{REPO}"


def api(method, path, body=None):
    url = f"{BASE}/contents/{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "audiogusano-migrate",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        if e.code == 404:
            return None
        raise RuntimeError(f"{method} {path}: {e.code} {msg}")


def slugify(value):
    name, ext = os.path.splitext(value)
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return f"{value or 'lanzamiento'}{ext.lower()}"


import yaml
with open(os.path.join(ROOT, "data", "lanzamientos.yml")) as f:
    entries = yaml.safe_load(f) or []

sidecar = {}
used = set()

for e in entries:
    link = e["link"]  # e.g. nuevos/dan.jpg
    dest = e["destination"]
    filename = os.path.basename(link)
    slug = slugify(filename)
    # unique slug for duplicate covers
    if slug in used:
        name, ext = os.path.splitext(slug)
        i = 2
        while f"{name}-{i}{ext}" in used:
            i += 1
        slug = f"{name}-{i}{ext}"
    used.add(slug)

    local_path = os.path.join(ROOT, "static", link)
    if not os.path.exists(local_path):
        print(f"MISSING {local_path}, skipping")
        continue
    with open(local_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    # commit file (get sha if exists)
    existing = api("GET", f"lanzamientos/{slug}")
    sha = existing.get("sha") if existing else None
    body = {"message": f"Lanzamiento: {slug}", "content": b64, "branch": BRANCH}
    if sha:
        body["sha"] = sha
    api("PUT", f"lanzamientos/{slug}", body)
    sidecar[slug] = dest
    print(f"uploaded {slug} -> {dest}")

# commit sidecar
sidecar_body = json.dumps(sidecar, indent=2, ensure_ascii=False)
b64 = base64.b64encode(sidecar_body.encode()).decode()
existing = api("GET", "lanzamientos/_lanzamientos.json")
sha = existing.get("sha") if existing else None
body = {"message": "Lanzamientos sidecar", "content": b64, "branch": BRANCH}
if sha:
    body["sha"] = sha
api("PUT", "lanzamientos/_lanzamientos.json", body)
print(f"sidecar committed with {len(sidecar)} entries")