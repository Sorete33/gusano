import os
import dropbox

# For local testing, you can paste your temporary access token here
# Or use the refresh token method we discussed
APP_KEY = "uax7zx5rnq30cpt"
APP_SECRET = "6mgbm49hx9dpo6i"
REFRESH_TOKEN = "vPtFZderFHUAAAAAAAAAAfZlNBCL81o1lsYsw1vtAB1oOSF30jqkmsqpAjqn1s7H"

def verify_connection():
    try:
        dbx = dropbox.Dropbox(
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            oauth2_refresh_token=REFRESH_TOKEN
        )
        
        # Test 1: Check account
        user = dbx.users_get_current_account()
        print(f"✅ Success! Connected to: {user.name.display_name}")

        # Test 2: Check Folder Path
        # NOTE: Use "" (empty string) to list the root folder if you aren't sure
        target_path = '/flyers'
        
        print(f"Searching for folder: {target_path}...")
        res = dbx.files_list_folder(target_path)
        
        print("\nFound these files:")
        for entry in res.entries:
            print(f" - {entry.name} ({type(entry).__name__})")

    except dropbox.exceptions.ApiError as e:
        print(f"❌ Folder Error: {e}")
        print("Tip: If you use 'App Folder' access, the path should likely be '' or '/'")
    except Exception as e:
        print(f"❌ General Error: {e}")

if __name__ == "__main__":
    verify_connection()