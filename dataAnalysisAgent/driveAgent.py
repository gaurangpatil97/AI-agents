import os
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ── SCOPES ────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly"
]

# ── AUTHENTICATE ──────────────────────────────────
def get_drive_service():
    creds = None

    # token.json stores the user's access token
    # auto generated on first run
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # if no valid token, login via browser
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # save token for next time
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


# ── FETCH CSV FROM DRIVE ──────────────────────────
def fetch_csv_from_drive(filename: str) -> str:
    """
    Search for a CSV file by name in Google Drive
    and save it locally. Returns local path.
    """
    try:
        service = get_drive_service()

        print(f"🔍 Searching Drive for: {filename}")

        # search for the file
        results = service.files().list(
            q=f"name='{filename}' and mimeType='text/csv'",
            spaces="drive",
            fields="files(id, name)"
        ).execute()

        files = results.get("files", [])

        if not files:
            return f"❌ File '{filename}' not found in Google Drive."

        # take the first match
        file_id = files[0]["id"]
        file_name = files[0]["name"]

        print(f"📥 Found: {file_name} — downloading...")

        # download it
        request = service.files().get_media(fileId=file_id)
        local_path = f"{filename}"

        with open(local_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        print(f"✅ Downloaded to: {local_path}")
        return local_path

    except Exception as e:
        return f"❌ Error fetching from Drive: {str(e)}"


# ── UPLOAD CHART TO DRIVE ─────────────────────────
def upload_chart_to_drive(local_path: str, folder_name: str = "AgentReports") -> str:
    """
    Upload a chart PNG to a folder in Google Drive.
    Creates the folder if it doesn't exist.
    """
    try:
        service = get_drive_service()

        # check if folder exists
        print(f"📁 Looking for folder: {folder_name}")
        results = service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
            spaces="drive",
            fields="files(id, name)"
        ).execute()

        folders = results.get("files", [])

        # create folder if it doesn't exist
        if not folders:
            print(f"📁 Creating folder: {folder_name}")
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = service.files().create(
                body=folder_metadata,
                fields="id"
            ).execute()
            folder_id = folder.get("id")
        else:
            folder_id = folders[0]["id"]

        # upload the file
        file_name = os.path.basename(local_path)
        print(f"📤 Uploading: {file_name}")

        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }

        media = MediaFileUpload(local_path, mimetype="image/png")

        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        link = uploaded.get("webViewLink")
        print(f"✅ Uploaded! View at: {link}")
        return link

    except Exception as e:
        return f"❌ Error uploading to Drive: {str(e)}"


# ── TEST ──────────────────────────────────────────
if __name__ == "__main__":
    print("🔐 Testing Google Drive connection...")
    service = get_drive_service()
    print("✅ Connected to Google Drive!")