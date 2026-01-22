import os
import dropbox
import yaml
import re
import unicodedata
from dropbox.exceptions import AuthError

# Configuration
DROPBOX_FOLDER_PATH = "/File requests/flyers"
LOCAL_STATIC_DIR = "static/images/gallery"
DATA_FILE = "data/flyers.yml"

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

def sync():
    os.makedirs(LOCAL_STATIC_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    try:
        dbx = dropbox.Dropbox(
            app_key=os.environ.get("DROPBOX_APP_KEY"),
            app_secret=os.environ.get("DROPBOX_APP_SECRET"),
            oauth2_refresh_token=os.environ.get("DROPBOX_REFRESH_TOKEN")
        )
        print("Connecting to Dropbox...")
    except Exception as e:
        print(f"Error: {e}")
        return

    try:
        res = dbx.files_list_folder(DROPBOX_FOLDER_PATH)
        dbx_files = [entry for entry in res.entries if isinstance(entry, dropbox.files.FileMetadata)]
    except Exception as e:
        print(f"Error listing folder: {e}")
        return

    flyer_list = []
    # We track current local files to see what needs to be deleted
    current_local_files = os.listdir(LOCAL_STATIC_DIR)
    processed_filenames = []

    for entry in dbx_files:
        # CLEAN THE FILENAME HERE
        clean_name = slugify(entry.name)
        local_path = os.path.join(LOCAL_STATIC_DIR, clean_name)
        
        # Download if the clean version doesn't exist
        if clean_name not in current_local_files:
            print(f"Downloading: {entry.name} as {clean_name}")
            with open(local_path, "wb") as f:
                metadata, res = dbx.files_download(entry.path_lower)
                f.write(res.content)
        
        processed_filenames.append(clean_name)
        
        flyer_list.append({
            'link': f'/images/gallery/{clean_name}',
            'name': os.path.splitext(entry.name)[0] # Keep the original name for the UI label
        })

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