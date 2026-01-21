import os
import dropbox
import yaml
from dropbox.exceptions import AuthError

# Configuration
DROPBOX_FOLDER_PATH = "/File requests/flyers" # Folder in your Dropbox
LOCAL_STATIC_DIR = "static/images/gallery"    # Where images are saved
DATA_FILE = "data/flyers.yml"                # The YAML Hugo reads

def sync():
    # 1. Ensure local directories exist
    os.makedirs(LOCAL_STATIC_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    # 2. Connect to Dropbox
    try:
        dbx = dropbox.Dropbox(
            app_key=os.environ.get("DROPBOX_APP_KEY"),
            app_secret=os.environ.get("DROPBOX_APP_SECRET"),
            oauth2_refresh_token=os.environ.get("DROPBOX_REFRESH_TOKEN")
        )
        print("Connecting to Dropbox...")
    except Exception as e:
        print(f"Error connecting to Dropbox: {e}")
        return

    # 3. List files in Dropbox
    try:
        res = dbx.files_list_folder(DROPBOX_FOLDER_PATH)
        dbx_files = [entry for entry in res.entries if isinstance(entry, dropbox.files.FileMetadata)]
    except Exception as e:
        print(f"Error listing folder: {e}")
        return

    flyer_list = []
    current_local_files = os.listdir(LOCAL_STATIC_DIR)
    downloaded_filenames = []

    # 4. Download files
    for entry in dbx_files:
        filename = entry.name
        local_path = os.path.join(LOCAL_STATIC_DIR, filename)
        
        # Only download if it doesn't exist locally
        if filename not in current_local_files:
            print(f"Downloading: {filename}")
            with open(local_path, "wb") as f:
                metadata, res = dbx.files_download(entry.path_lower)
                f.write(res.content)
        
        downloaded_filenames.append(filename)
        
        # 5. Format the link for Hugo
        # We use /images/gallery/ because 'static' is the root in Hugo
        flyer_list.append({
            'link': f'/images/gallery/{filename}',
            'name': filename
        })

    # 6. Cleanup local files that were deleted from Dropbox
    for local_f in current_local_files:
        if local_f not in downloaded_filenames:
            print(f"Removing deleted file: {local_f}")
            os.remove(os.path.join(LOCAL_STATIC_DIR, local_f))

    # 7. Save the YAML file
    with open(DATA_FILE, 'w') as yml_out:
        yaml.dump(flyer_list, yml_out, default_flow_style=False, sort_keys=False)

    print(f"✅ Sync complete. {len(flyer_list)} items in {DATA_FILE}")

if __name__ == "__main__":
    sync()
