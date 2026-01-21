import os
import dropbox
import yaml

# CONFIGURATION
APP_KEY = os.environ.get('DROPBOX_APP_KEY')
APP_SECRET = os.environ.get('DROPBOX_APP_SECRET')
REFRESH_TOKEN = os.environ.get('DROPBOX_REFRESH_TOKEN')

# Use the path from your link (must start with /)
DROPBOX_FOLDER_PATH = '/File requests/flyers' 
LOCAL_IMG_DIR = 'static/images/gallery'
DATA_FILE = 'data/flyers.yml'
WEB_PATH_PREFIX = '/images/gallery/'

def sync():
    dbx = dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN
    )

    if not os.path.exists(LOCAL_IMG_DIR):
        os.makedirs(LOCAL_IMG_DIR)

    print(f"Connecting to Dropbox: {DROPBOX_FOLDER_PATH}...")
    
    try:
        res = dbx.files_list_folder(DROPBOX_FOLDER_PATH)
        
        gallery_data = []
        current_local_files = []

        for entry in res.entries:
            if isinstance(entry, dropbox.files.FileMetadata):
                # We only want images and videos
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webp']:
                    
                    local_path = os.path.join(LOCAL_IMG_DIR, entry.name)
                    current_local_files.append(entry.name)
                    
                    # Download the file
                    print(f"Downloading: {entry.name}")
                    with open(local_path, "wb") as f:
                        metadata, response = dbx.files_download(entry.path_lower)
                        f.write(response.content)
                    
                    # Add to YAML list
                    gallery_data.append({
                        'link': f"{WEB_PATH_PREFIX}{entry.name}"
                    })

        # --- CLEANUP LOGIC ---
        # Remove files from local folder if they were deleted from Dropbox
        for local_file in os.listdir(LOCAL_IMG_DIR):
            if local_file not in current_local_files:
                print(f"Removing deleted file: {local_file}")
                os.remove(os.path.join(LOCAL_IMG_DIR, local_file))

        # Update the YAML file for Hugo
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w') as f:
            yaml.dump(gallery_data, f, default_flow_style=False)
        
        print(f"✅ Sync complete. {len(gallery_data)} items in gallery.")

    except Exception as e:
        print(f"❌ Error during sync: {e}")

if __name__ == "__main__":
    sync()