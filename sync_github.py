"""Pull band flyers out of the public audiogusano-flyers repo into the site.

Replaces the old Dropbox sync: the Dropbox "File requests" folder is gone, and
bands now drop flyers into https://github.com/Sorete33/audiogusano-flyers (the
browser upload button on the home page commits straight into `flyers/`).

Everything downstream of the download -- slugification, the manual `ribbon`
field preservation in data/flyers.yml, deleting files that no longer exist
upstream -- is deliberately identical to the Dropbox version, so data/flyers.yml
stays the contract the gallery shortcode reads.
"""
import base64
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
FLYERS_PATH = os.environ.get("FLYERS_PATH", "flyers")
FLYERS_BRANCH = os.environ.get("FLYERS_BRANCH", "main")
LOCAL_STATIC_DIR = "static/images/gallery"
DATA_FILE = "data/flyers.yml"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

# Extensions worth pulling into the gallery. The site is a Neocities Supporter
# account, which has no upload whitelist and deploys with
# neocities_supporter:true, so .mp4 is included here and reaches the site as
# .mp4 -- no conversion. Keep in sync with scripts/check-neocities-types.py.
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".mp4"}

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
            ext = os.path.splitext(name)[1].lower()
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
    request = urllib.request.Request(
        download_url(entry),
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "audiogusano-flyer-sync",
        }
    )
    if GITHUB_TOKEN:
        request.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
    except Exception as e:
        print(f"Error downloading {entry['raw_path']}: {e}")
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

    with open(destination, "wb") as f:
        f.write(payload)
    return True


def download_url(entry):
    """Where to GET one remote file's bytes."""
    if entry.get("sha"):
        return (f"https://api.github.com/repos/{FLYERS_REPO}/git/blobs/{entry['sha']}")
    # Fallback for a listing that somehow lacked a sha; percent-encode it,
    # because the raw path can contain spaces and accents.
    if entry.get("download_url"):
        return urllib.parse.quote(entry["download_url"], safe=":/?&=%#")
    return ""


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


def sync():
    os.makedirs(LOCAL_STATIC_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    existing_entries = load_existing_entries()

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

        processed_filenames.append(clean_name)

        flyer_entry = {
            'link': f'/images/gallery/{clean_name}',
            'name': os.path.splitext(entry['name'])[0]  # Keep the original name for the UI label
        }

        # Preserve manual fields (e.g. ribbon) added by hand in the repo
        previous = existing_entries.get(flyer_entry['link'])
        if previous:
            for key in ('ribbon',):
                if previous.get(key):
                    flyer_entry[key] = previous[key]

        flyer_list.append(flyer_entry)

    # Cleanup: Remove files that don't match our processed list
    for local_f in current_local_files:
        if local_f not in processed_filenames:
            print(f"Removing old/unmatched file: {local_f}")
            os.remove(os.path.join(LOCAL_STATIC_DIR, local_f))

    with open(DATA_FILE, 'w') as yml_out:
        yaml.dump(flyer_list, yml_out, default_flow_style=False, sort_keys=False)

    print(f"✅ Sync complete. {len(flyer_list)} items in {DATA_FILE}")


if __name__ == "__main__":
    sync()