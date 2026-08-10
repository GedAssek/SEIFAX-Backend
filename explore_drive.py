"""
Script utilitaire pour récupérer les noms de dossiers depuis Google Drive
et identifier quels matières appartiennent à quelle année.
Ce script utilise les mêmes credentials que le backend.
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from googleapiclient.discovery import build
from google.oauth2 import service_account

ROOT_FOLDER_IDS = [
    "1XUQZ9-mfHrX9O9796e9xyZtVvRlFf-U2",
    "1Ue1s2Vp8bDSY99ra_95d1X_qZ1arNlPA",
    "18bjsPtNCfR7_49U-X4V-eQCOkiWybX_n"
]

def get_drive_service():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        return build('drive', 'v3', credentials=creds)
    api_key = os.getenv("GOOGLE_DRIVE_API_KEY")
    if api_key:
        return build('drive', 'v3', developerKey=api_key)
    raise ValueError("Aucune credential trouvée")

def list_drive_files(service, parent_id):
    results = []
    page_token = None
    while True:
        try:
            response = service.files().list(
                q=f"'{parent_id}' in parents and trashed=false",
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token
            ).execute()
            for file in response.get('files', []):
                results.append(file)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        except Exception as e:
            print(f"Erreur Drive API: {e}")
            break
    return results

if __name__ == "__main__":
    try:
        service = get_drive_service()
    except Exception as e:
        print(f"Erreur initialisation: {e}")
        exit(1)

    for root_id in ROOT_FOLDER_IDS:
        try:
            root_info = service.files().get(fileId=root_id, fields='name').execute()
            root_name = root_info.get('name', 'Inconnu')
            print(f"\n=== Racine: {root_name} ===")
        except Exception as e:
            print(f"Erreur racine {root_id}: {e}")
            continue

        level1 = list_drive_files(service, root_id)
        for l1 in level1:
            print(f"  [{l1['mimeType'].split('.')[-1]}] {l1['name']}")
            if l1['mimeType'] == 'application/vnd.google-apps.folder':
                level2 = list_drive_files(service, l1['id'])
                for l2 in level2:
                    print(f"    [{l2['mimeType'].split('.')[-1]}] {l2['name']}")
