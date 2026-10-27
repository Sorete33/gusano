"""Pull band flyers out of the public audiogusano-flyers repo into the site.

Replaces the old Dropbox sync: the Dropbox "File requests" folder is gone, and
bands now drop flyers into https://github.com/Sorete33/audiogusano-flyers (the
browser upload button on the home page commits straight into `flyers/`).

Everything downstream of the download -- slugification, the manual `ribbon`
field preservation in data/flyers.yml, deleting files that no longer exist
upstream -- is deliberately identical to the Dropbox version, so data/flyers.yml
stays the contract the gallery shortcode reads.
"""
import argparse
import base64
import datetime
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

import yaml

# Configuration
FLYERS_REPO = os.environ.get("FLYERS_REPO", "Sorete33/audiogusano-flyers")
FLYERS_BRANCH = os.environ.get("FLYERS_BRANCH", "main")

SECTIONS = {
    "flyers": {
        "remote_path": os.environ.get("FLYERS_PATH", "flyers"),
        "local_dir": "static/images/gallery",
        "data_file": "data/flyers.yml",
        "sidecar": "_dates.json",
        "preserve": ("ribbon", "date"),
    },
    "lanzamientos": {
        "remote_path": os.environ.get("LAUNCHES_PATH", "lanzamientos"),
        "local_dir": "static/nuevos",
        "data_file": "data/lanzamientos.yml",
        "sidecar": "_lanzamientos.json",
        "preserve": ("destination", "date"),
    },
}

# Active section (set by configure())
SECTION = "flyers"
FLYERS_PATH = SECTIONS[SECTION]["remote_path"]
LOCAL_STATIC_DIR = SECTIONS[SECTION]["local_dir"]
DATA_FILE = SECTIONS[SECTION]["data_file"]
SIDECAR = SECTIONS[SECTION]["sidecar"]
PRESERVE_FIELDS = SECTIONS[SECTION]["preserve"]


def configure(section):
    global SECTION, FLYERS_PATH, LOCAL_STATIC_DIR, DATA_FILE, SIDECAR, PRESERVE_FIELDS
    if section not in SECTIONS:
        raise SystemExit(f"Unknown section: {section}")
    SECTION = section
    cfg = SECTIONS[section]
    FLYERS_PATH = cfg["remote_path"]
    LOCAL_STATIC_DIR = cfg["local_dir"]
    DATA_FILE = cfg["data_file"]
    SIDECAR = cfg["sidecar"]
    PRESERVE_FIELDS = cfg["preserve"]

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
VERBOSE = False

# Extensions worth pulling into the gallery. The site is a Neocities Supporter
# account, which has no upload whitelist and deploys with
# neocities_supporter:true, so .mp4 is included here and reaches the site as
# .mp4 -- no conversion. Keep in sync with scripts/check-neocities-types.py.
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".mp4"}

# Tamaño máximo por archivo (10 MB).
MAX_FILE_SIZE = 10 * 1024 * 1024

# Extensiones peligrosas (bloqueadas siempre, incluso en supporter).
DANGEROUS_EXTENSIONS = {".exe", ".sh", ".php", ".cgi", ".pl", ".py", ".bat", ".cmd"}

# The GitHub contents API returns at most 1000 entries per directory listing and
# gives no way to page past that, so a folder at the cap is almost certainly
# truncated and would be worth failing loudly over.
LISTING_CAP = 1000


def slugify(value):
    """
    Converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    # Split filename and extension
    name, ext = os.path.splitext(value)

    value = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    value = re.sub(r'[-\s]+', '-', value)

    return f"{value}{ext.lower()}"


def is_safe_name(name):
    """Rechaza nombres con path traversal o caracteres peligrosos."""
    if not name or not isinstance(name, str):
        return False
    if name.startswith(".") or name.startswith("/"):
        return False
    if ".." in name or "/" in name or "\\" in name:
        return False
    if any(ord(c) < 32 for c in name):
        return False
    return True

def api_get(url):
    """GET a GitHub API URL with auth, returning parsed JSON."""
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "audiogusano-flyer-sync",
    })
    if GITHUB_TOKEN:
        request.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def list_remote_files():
    """Every image file under FLYERS_PATH, recursing into subdirectories."""
    collected = []
    pending = [FLYERS_PATH]

    while pending:
        current = pending.pop()
        url = (f"https://api.github.com/repos/{FLYERS_REPO}/contents/{current}"
               f"?ref={FLYERS_BRANCH}")
        try:
            entries = api_get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Warning: {current} not found in {FLYERS_REPO}")
                return collected
            print(f"Error listing {current}: {e}")
            return None
        except urllib.error.URLError as e:
            print(f"Error listing {current}: {e.reason}")
            return None

        if not isinstance(entries, list):
            print(f"Error: expected a listing for {current}, got {type(entries).__name__}")
            return None

        if len(entries) >= LISTING_CAP:
            print(f"Error: {current} hit the {LISTING_CAP}-entry API cap and is "
                  f"truncated. Move the flyers into subdirectories.")
            return None

        for entry in entries:
            if entry.get("type") == "dir":
                pending.append(entry["path"])
                continue
            if entry.get("type") != "file":
                continue

            name = entry.get("name") or ""
            # Seguridad: rechazar nombres con path traversal o caracteres peligrosos.
            if not is_safe_name(name):
                print(f"Skipping unsafe filename: {entry.get('path')}")
                continue
            # Sidecar metadata and dotfiles are not gallery assets; skip them
            # silently instead of warning about an unknown extension.
            if name.startswith('.') or name.startswith('_'):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in DANGEROUS_EXTENSIONS:
                print(f"Skipping dangerous file: {entry.get('path')}")
                continue
            if ext not in ALLOWED_EXTENSIONS:
                print(f"Skipping {entry['path']}: .{ext or '?'} is not something "
                      f"the gallery renders. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
                continue

            collected.append({
                "name": name,
                "download_url": entry.get("download_url"),
                "raw_path": entry["path"],
                "sha": entry.get("sha"),
            })

    return collected


def download(entry, destination):
    """Fetch one remote file to a local path."""
    # Path traversal guard: verificar destino real.
    allowed_dir = os.path.realpath(LOCAL_STATIC_DIR)
    real_dest = os.path.realpath(destination)
    if not (real_dest == os.path.join(allowed_dir, os.path.basename(real_dest))
            and real_dest.startswith(allowed_dir + os.sep)):
        print(f"Refusing to write outside allowed dir: {destination}")
        return False

    url = download_url(entry)
    if not url:
        print(f"No download URL for {entry['raw_path']}")
        return False

    last_err = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "audiogusano-flyer-sync",
                }
            )
            if GITHUB_TOKEN:
                request.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")

            with urllib.request.urlopen(request, timeout=120) as response:
                # Content-Length check
                cl = response.headers.get("Content-Length")
                if cl and int(cl) > MAX_FILE_SIZE:
                    print(f"File too large ({cl} bytes), skipping: {entry['raw_path']}")
                    return False
                payload = response.read()
            if len(payload) > MAX_FILE_SIZE:
                print(f"File too large ({len(payload)} bytes), skipping: {entry['raw_path']}")
                return False

            # The blob endpoint answers with base64; download_url does not. Band names
            # are full of accents and spaces, which urllib refuses to put in a URL, so
            # the blob endpoint is the only encoding-safe option for those filenames.
            if entry.get("sha"):
                try:
                    payload = base64.b64decode(json.loads(payload)["content"])
                except (ValueError, KeyError) as e:
                    print(f"Error decoding blob for {entry['raw_path']}: {e}")
                    return False
                if len(payload) > MAX_FILE_SIZE:
                    print(f"File too large ({len(payload)} bytes), skipping: {entry['raw_path']}")
                    return False

            with open(destination, "wb") as f:
                f.write(payload)
            return True
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt+1}/3 failed for {entry['raw_path']}: {e}")
            if attempt < 2:
                import time
                time.sleep(2 ** attempt)

    print(f"Error downloading {entry['raw_path']}: {last_err}")
    return False


def download_url(entry):
    """Where to GET one remote file's bytes."""
    if entry.get("sha"):
        return (f"https://api.github.com/repos/{FLYERS_REPO}/git/blobs/{entry['sha']}")
    # Fallback for a listing that somehow lacked a sha; percent-encode it,
    # because the raw path can contain spaces and accents.
    if entry.get("download_url"):
        return urllib.parse.quote(entry["download_url"], safe=":/?&=%#")
    return ""


def normalize_date(value):
    """Normalize a date value to ISO YYYY-MM-DD.

    Accepts datetime/date objects and strings in ISO (YYYY-MM-DD) or
    local DD-MM-YYYY / DD/MM/YYYY form. Returns None for empty input.
    """
    if value is None:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime('%Y-%m-%d')
    s = str(value).strip()
    if not s:
        return None
    import re
    if re.fullmatch(r'\d{4}-\d{1,2}-\d{1,2}', s):
        y, m, d = s.split('-')
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    m = re.fullmatch(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', s)
    if m:
        d, mo, y = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    return s


def load_existing_entries():
    """Load current data/flyers.yml to preserve manual fields the sync does not know about."""
    existing = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                for item in yaml.safe_load(f) or []:
                    if isinstance(item, dict) and item.get('link'):
                        existing[item['link']] = item
        except Exception as e:
            print(f"Warning: could not read existing {DATA_FILE}: {e}")
    return existing


def load_remote_sidecar():
    """Fetch the section sidecar (slug -> metadata) if present."""
    url = (f"https://api.github.com/repos/{FLYERS_REPO}/contents/{FLYERS_PATH}/{SIDECAR}"
           f"?ref={FLYERS_BRANCH}")
    try:
        entry = api_get(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        print(f"Warning: could not fetch {SIDECAR}: HTTP {e.code}")
        return {}
    except Exception as e:
        print(f"Warning: could not fetch {SIDECAR}: {e}")
        return {}
    if not isinstance(entry, dict) or not entry.get('content'):
        return {}
    try:
        import base64 as _b64
        payload = _b64.b64decode(entry['content'])
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    except Exception as e:
        print(f"Warning: could not parse {SIDECAR}: {e}")
    return {}


def sync():
    os.makedirs(LOCAL_STATIC_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    existing_entries = load_existing_entries()
    remote_sidecar = load_remote_sidecar()
    print(f"Connecting to GitHub ({FLYERS_REPO}@{FLYERS_BRANCH}, path /{FLYERS_PATH})...")
    remote_files = list_remote_files()
    if remote_files is None:
        sys.exit(1)

    flyer_list = []
    # We track current local files to see what needs to be deleted
    current_local_files = os.listdir(LOCAL_STATIC_DIR)
    processed_filenames = []

    for entry in remote_files:
        clean_name = slugify(entry['name'])
        local_path = os.path.join(LOCAL_STATIC_DIR, clean_name)

        if clean_name not in current_local_files:
            print(f"Downloading: {entry['raw_path']} as {clean_name}")
            if not download(entry, local_path):
                # Leave the file out of flyers.yml rather than publishing a
                # gallery card that points at nothing.
                continue
        else:
            if VERBOSE:
                print(f"Already present, not overwriting: {clean_name}")

        processed_filenames.append(clean_name)

        if SECTION == "lanzamientos":
            link_prefix = "/nuevos"
        else:
            link_prefix = "/images/gallery"
        flyer_entry = {
            'link': f'{link_prefix}/{clean_name}',
            'name': os.path.splitext(entry['name'])[0]  # Keep the original name for the UI label
        }

        # Preserve manual fields and apply sidecar metadata.
        previous = existing_entries.get(flyer_entry['link'])
        # Sidecar takes precedence for its known field(s).
        if clean_name in remote_sidecar:
            meta = remote_sidecar[clean_name]
            if SECTION == "flyers":
                nd = normalize_date(meta if not isinstance(meta, dict) else meta.get("date"))
                if nd:
                    flyer_entry['date'] = nd
            else:
                if isinstance(meta, dict):
                    if meta.get("destination"):
                        flyer_entry['destination'] = meta["destination"]
                    if meta.get("date"):
                        nd = normalize_date(meta["date"])
                        if nd:
                            flyer_entry['date'] = nd
                else:
                    if meta:
                        flyer_entry['destination'] = meta
        if previous:
            for key in PRESERVE_FIELDS:
                if key not in flyer_entry and previous.get(key):
                    val = previous.get(key)
                    if key == "date":
                        val = normalize_date(val)
                    if val:
                        flyer_entry[key] = val

        flyer_list.append(flyer_entry)

    # Cleanup: Remove files that don't match our processed list
    for local_f in current_local_files:
        if local_f not in processed_filenames:
            print(f"Removing old/unmatched file: {local_f}")
            os.remove(os.path.join(LOCAL_STATIC_DIR, local_f))

    with open(DATA_FILE, 'w') as yml_out:
        yaml.dump(flyer_list, yml_out, default_flow_style=False, sort_keys=False)

    print(f"✅ Sync complete. {len(flyer_list)} items in {DATA_FILE}")


def main():
    global VERBOSE
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", choices=sorted(SECTIONS), default="flyers")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug output")
    args = parser.parse_args()
    VERBOSE = args.verbose
    configure(args.section)
    sync()


if __name__ == "__main__":
    main()