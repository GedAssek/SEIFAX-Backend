import os
import re
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

from googleapiclient.discovery import build
from google.oauth2 import service_account
from database.db import connect_db, close_db, get_db

load_dotenv()

# Liste des IDs des dossiers racines fournis par l'utilisateur
ROOT_FOLDER_IDS = [
    "1XUQZ9-mfHrX9O9796e9xyZtVvRlFf-U2",
    "1Ue1s2Vp8bDSY99ra_95d1X_qZ1arNlPA",
    "18bjsPtNCfR7_49U-X4V-eQCOkiWybX_n"
]

def get_drive_service():
    # 1. Essayer avec le fichier JSON du Compte de Service (recommandé)
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        return build('drive', 'v3', credentials=creds)
        
    # 2. Sinon, essayer avec la clé API (dossiers publics uniquement)
    api_key = os.getenv("GOOGLE_DRIVE_API_KEY")
    if api_key:
        return build('drive', 'v3', developerKey=api_key)
        
    raise ValueError("Ni GOOGLE_APPLICATION_CREDENTIALS ni GOOGLE_DRIVE_API_KEY ne sont définis.")

def determine_type(filename: str) -> str:
    name_lower = filename.lower()
    
    # Cours
    if any(kw in name_lower for kw in ['module', 'support', 'cours', 'doc']):
        return 'cours'
    # TP/TD
    elif any(kw in name_lower for kw in ['td', 'exo', 'sujet']):
        return 'tp'
    # Evaluation (fallback pour 'copie', 'interro', 'examen' et le reste)
    else:
        return 'evaluation'

def parse_cycle_annee(folder_name: str):
    """
    Tente d'extraire le cycle, l'année calendaire et l'année d'étude depuis le nom du dossier.
    Exemples: EAC_SEI1_2024 -> cycle=EAC-SEI, annee=2024, annee_etude=1
              EAC_NA_2èmeAnnee_2023 -> cycle=EAC-NA, annee=2023, annee_etude=2
    """
    annee = 2024  # fallback année calendaire
    cycle = "EAC-SEI"  # fallback cycle
    annee_etude = None  # fallback : pas de restriction par année d'étude
    
    # Recherche de l'année calendaire (4 chiffres commençant par 20)
    match_annee = re.search(r'(20\d{2})', folder_name)
    if match_annee:
        annee = int(match_annee.group(1))
    
    # Détection de l'année d'étude (1, 2, 3)
    # Patterns: SEI1, SEI2, SEI3, 1ere, 2eme, 3eme, AN1, AN2, AN3, A1, A2, A3
    name_upper = folder_name.upper()
    match_etude = re.search(r'(?:SEI|NA|MTO?|AN|A)[\s_-]?([123])|([123])(?:ERE|EME|ÈME|E)[\s_-]*ANN[EÉ]E', name_upper)
    if match_etude:
        annee_etude = int(match_etude.group(1) or match_etude.group(2))
    else:
        # Essai de trouver un chiffre isolé (ex: 1, 2, 3) dans le nom du dossier
        match_num = re.search(r'(?<![0-9])([123])(?![0-9])', folder_name)
        if match_num:
            annee_etude = int(match_num.group(1))
        
    # Extraction du cycle
    if 'IEAMAC' in name_upper:
        if 'SEI' in name_upper: cycle = "IEAMAC-SEI"
        elif 'NA' in name_upper: cycle = "IEAMAC-NA"
        elif 'M' in name_upper: cycle = "IEAMAC-M"
    elif 'EAC' in name_upper:
        if 'SEI' in name_upper: cycle = "EAC-SEI"
        elif 'NA' in name_upper: cycle = "EAC-NA"
        elif 'M' in name_upper: cycle = "EAC-M"
    elif 'CCA' in name_upper:
        cycle = "CCA"
    elif 'T' in name_upper:
        if 'NA' in name_upper: cycle = "T-NA"
        elif 'M' in name_upper: cycle = "T-M"

    return cycle, annee, annee_etude

async def list_drive_files(service, parent_id: str) -> List[Dict]:
    """Récupère tous les fichiers/dossiers enfants d'un dossier donné (non-bloquant)."""
    results = []
    page_token = None
    while True:
        try:
            await asyncio.sleep(0) # Rend la main à la boucle d'événements
            response = service.files().list(
                q=f"'{parent_id}' in parents and trashed=false",
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, webViewLink, createdTime)',
                pageToken=page_token
            ).execute()
            
            for file in response.get('files', []):
                results.append(file)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        except Exception as e:
            print(f"Erreur Drive API pour le dossier {parent_id}: {e}")
            raise e
    return results

async def sync_drive_to_db(standalone=False):
    try:
        service = get_drive_service()
    except Exception as e:
        print(f"Erreur d'initialisation Google Drive: {e}")
        return False, str(e)

    if standalone:
        try:
            await connect_db()
        except Exception as e:
            pass
        
    db = get_db()
    if db is None:
        return False, "Database not connected"

    # Collection cible
    docs_coll = db["documents"]
    
    total_inserted = 0
    total_skipped = 0
    
    for root_id in ROOT_FOLDER_IDS:
        print(f"Analyse de la racine: {root_id}")
        try:
            await asyncio.sleep(0)
            root_info = service.files().get(fileId=root_id, fields='name').execute()
            root_name = root_info.get('name', 'Inconnu')
        except Exception as e:
            print(f"Failed to get root_info for {root_id}: {e}")
            continue
            
        print(f"  -> Nom du dossier racine: {root_name}")
        
        level1_items = await list_drive_files(service, root_id)
        
        for l1 in level1_items:
            if l1['mimeType'] == 'application/vnd.google-apps.folder':
                # Si le nom contient une année ou "annee", c'est probablement le niveau "Cycle/Année"
                if re.search(r'(20\d{2}|annee|ann.e)', l1['name'].lower()):
                    cycle, annee, annee_etude = parse_cycle_annee(l1['name'])
                    
                    level2_items = await list_drive_files(service, l1['id'])
                    for l2 in level2_items:
                        if l2['mimeType'] == 'application/vnd.google-apps.folder':
                            matiere = l2['name']
                            
                            files = await list_drive_files(service, l2['id'])
                            for f in files:
                                if f['mimeType'] != 'application/vnd.google-apps.folder':
                                    res = await process_and_insert_file(docs_coll, f, matiere, cycle, annee, annee_etude)
                                    if res: total_inserted += 1
                                    else: total_skipped += 1
                                    
                else:
                    matiere = l1['name']
                    cycle, annee, annee_etude = parse_cycle_annee(root_name)
                    
                    files = await list_drive_files(service, l1['id'])
                    for f in files:
                        if f['mimeType'] != 'application/vnd.google-apps.folder':
                            res = await process_and_insert_file(docs_coll, f, matiere, cycle, annee, annee_etude)
                            if res: total_inserted += 1
                            else: total_skipped += 1

    if standalone:
        try:
            await close_db()
        except:
            pass
        
    return True, f"Synchronisation terminée. {total_inserted} documents ajoutés. {total_skipped} déjà existants (annee_etude mis à jour si nécessaire)."


async def fix_annee_etude_only(standalone=False):
    """
    Parcourt Google Drive et met à jour annee_etude de TOUS les documents
    existants en base, sans insérer de nouveaux. Utile pour corriger
    des documents importés avant la correction du regex.
    """
    try:
        service = get_drive_service()
    except Exception as e:
        print(f"Erreur d'initialisation Google Drive: {e}")
        return False, str(e)

    if standalone:
        try:
            await connect_db()
        except Exception as e:
            pass

    db = get_db()
    if db is None:
        return False, "Database not connected"

    docs_coll = db["documents"]
    total_updated = 0
    total_skipped = 0

    for root_id in ROOT_FOLDER_IDS:
        try:
            await asyncio.sleep(0)
            root_info = service.files().get(fileId=root_id, fields='name').execute()
            root_name = root_info.get('name', 'Inconnu')
        except Exception as e:
            print(f"Erreur racine {root_id}: {e}")
            continue

        print(f"  -> Fix annee_etude dans: {root_name}")
        level1_items = await list_drive_files(service, root_id)

        for l1 in level1_items:
            if l1['mimeType'] == 'application/vnd.google-apps.folder':
                if re.search(r'(20\d{2}|annee|ann.e)', l1['name'].lower()):
                    cycle, annee, annee_etude = parse_cycle_annee(l1['name'])
                    level2_items = await list_drive_files(service, l1['id'])
                    for l2 in level2_items:
                        if l2['mimeType'] == 'application/vnd.google-apps.folder':
                            files = await list_drive_files(service, l2['id'])
                            for f in files:
                                if f['mimeType'] != 'application/vnd.google-apps.folder':
                                    file_url = f.get('webViewLink', '')
                                    if not file_url:
                                        continue
                                    existing = await docs_coll.find_one({"file_url": file_url})
                                    if existing and annee_etude is not None:
                                        await docs_coll.update_one(
                                            {"_id": existing["_id"]},
                                            {"$set": {"annee_etude": annee_etude}}
                                        )
                                        total_updated += 1
                                    else:
                                        total_skipped += 1
                else:
                    cycle, annee, annee_etude = parse_cycle_annee(root_name)
                    files = await list_drive_files(service, l1['id'])
                    for f in files:
                        if f['mimeType'] != 'application/vnd.google-apps.folder':
                            file_url = f.get('webViewLink', '')
                            if not file_url:
                                continue
                            existing = await docs_coll.find_one({"file_url": file_url})
                            if existing and annee_etude is not None:
                                await docs_coll.update_one(
                                    {"_id": existing["_id"]},
                                    {"$set": {"annee_etude": annee_etude}}
                                )
                                total_updated += 1
                            else:
                                total_skipped += 1

    if standalone:
        try:
            await close_db()
        except:
            pass

    return True, f"Correction terminée. {total_updated} documents mis à jour. {total_skipped} ignorés (annee_etude déjà None dans Drive ou doc non trouvé)."

async def process_and_insert_file(docs_coll, file_item, matiere, cycle, annee, annee_etude=None) -> bool:
    file_name = file_item['name']
    file_url = file_item.get('webViewLink', '')
    
    existing = await docs_coll.find_one({"file_url": file_url})
    if existing:
        # Mettre à jour annee_etude si elle n'était pas définie auparavant
        if annee_etude is not None and existing.get('annee_etude') is None:
            await docs_coll.update_one({"_id": existing["_id"]}, {"$set": {"annee_etude": annee_etude}})
        return False
        
    doc_type = determine_type(file_name)
    
    cat_eval = None
    if doc_type == 'evaluation':
        name_lower = file_name.lower()
        if 'interro' in name_lower: cat_eval = 'interro'
        elif 'compo' in name_lower: cat_eval = 'compo'
        elif 'examen' in name_lower: cat_eval = 'examen'
        
    doc = {
        "titre": file_name,
        "type": doc_type,
        "categorie_eval": cat_eval,
        "matiere": matiere,
        "cycle": cycle,
        "annee": annee,
        "annee_etude": annee_etude,  # Niveau d'étude (1, 2, 3 ou None pour tous)
        "file_url": file_url,
        "uploaded_by": "System (Drive Sync)",
        "created_at": datetime.now().isoformat()
    }
    
    await docs_coll.insert_one(doc)
    return True

# ─── Mapping matière → année d'étude (EAC-SEI) ──────────────────────────────
# Ce mapping permet de corriger annee_etude sans connexion à Google Drive
MATIERE_ANNEE_MAP_RAW = {
    # === 1ère ANNÉE (fondamentaux) ===
    1: [
        'ELECTRONIQUE FONDAMENTALE', 'ELECTRONIQUE FONDAMENTALES', 'TP ELECTRONIQUE FONDAMENTALE',
        '\u00c9LECTRONIQUE FONDAMENTALES',
        'CIRCUITS ELECTRIQUES', 'ELECTRICITE GENERAL',
        'ALGORITHME ET PROGRAMMATION', "ALGORITHME ET PROGRAMMATION 'C'",
        'BUREAUTIQUE', 'INFORMATIQUE',
        'ANGLAIS GENERAL', 'ANGLAIS TECHNIQUE', 'ANGLAIS TECHNIQUE ET PROFESSIONNEL',
        'SECOURISME',
        'REDACTION ADMINISTRATIVE', 'RÉDACTION ADMINISTRATIVE', 'R\u00c9DACTION ADMINISTRATIVE',
        'AOP',
        'ELECTRONIQUE NUMERIQUE',
        'MICROPROCESSEUR-MICROCONTROLEUR', 'MICROPROCESEUR-MICROCONTROLLEUR',
        'MACHINE ELECTRIQUE',
        'ELECTRONIQUE DE PUISSANCE',
        'TECHNOLOGIES,MATERIELS ET COMPOSANTS ELECTRIQUES',
        'APPAREILS DE MESURE POUR ELECTRICIEN',
        'APPAREILS DE MESURE POUR ELECTRONICIEN',
        'MATERIEL ELECTRIQUE',
        'ARCHITECTURE ET CONFIGURATION DES PC', 'ARCHITECHTURE ET CONFIG PC',
        'FACTEURS HUMAINS',
        'GESTION DE CHANTIER ( CONDUITE ATTITUDE PREVENTION DES ACCIDENTS', 'GESTION DE CHANTIER',
        'ANNEXES',
    ],
    # === 2ème ANNÉE (transmission, navigation, radio) ===
    2: [
        'ANTENNES',
        'EMISSION-RECEPTION', 'EMISSION RECEPTION',
        'LIGNES ET HYPERFREQUENCES',
        'PROPAGATION EN ESPACE LIBRE',
        'VOR',
        'ILS',
        'DME',
        'GNSS',
        'NAVIGATION',
        'METEOROLOGIE',
        'ADS', 'ADS ALABE',
        'MULTILATERATION', 'MLAT',
        'BALISAGE LUMINEUX',
        'CHAINE RADIO',
        'EQUIPEMENT VHF',
        'AEROTECHNIQUE',
        "COURS DE SAUVETAGE ET DE LUTTE  CONTRE L'INCENDIE SUR LES AEROPORTS",
        'FAISCEAU HERTZIEN',
        'AUTOMATIQUE',
        'TECHNIQUES SATELLITAIRES', 'TECHNIQUE SATELLITAIRE',
        'TRANSMISSION DES DONNÉES', 'TRANSMISSION DES DONNEES', 'TRANSMISSION DES DONN\u00c9ES',
        'TRANSPORT DES DONNEES',
        'RADAR MTO', 'RADIOSONDAGE', 'RADIOSONDAGE MTO', 'RADAR METEO', 'RADAR M\u00c9T\u00c9O',
        "SYSTEME DE PRODUCTION ET DE GESTION D'ENERGIE ELECTRIQUE",
        'TRANSPORT ET DISTRIBUTION \u00c9LECTRIQUE', 'TRANSPORT ET DISTRIBUTION ELECTRIQUE',
    ],
    # === 3ème ANNÉE (spécialisation, systèmes avancés) ===
    3: [
        'OIACM', 'COURS OIACM',
        'SAAPI',
        'SAOMA',
        'SURVEILLANCE',
        'RCA',
        'COMMUNICATION ATM',
        'SSLI',
        'INTRODUCTION AU RESEAU', 'RESEAUX',
        'LES PROTOCOLES',
        'RESEAU NATIONAUX', 'RESEAUX INTERNATIONAUX',
        'BASE DE DONNEES',
        'SGBD',
        "SYS D'EXPLOITATION ( LINUX-WINDOWS )",
        'SE LINUX',
        'PARE-FEU',
        'VPN',
        'ROUTEUR',
        'TELEPHONIE',
        'COMMUTATION VOIX ET DONNEES',
        'COMMUTATEUR DE MESSAGES',
        'SYST DE CHAINES DE RADIOTELEPHONIE ( VCCS )',
        'ETUDE DE MATERIELS-EQUIPMNTS VSAT ET ENERGIE',
        'ETUDES DE MATERIELS MULTIPLEXEURS ET COMMUTATEUR',
        'TRAITEMENT DE DONNEES DE SURVEILLANCE',
        'RADAR DE CONTROLE AERIEN', 'RADAR DU CONTROLE AERIEN',
        "SYSTEME DE GESTION DE L'INFORMATION AERONAUTIQUE",
        'GESTION DE LA S\u00c9CURIT\u00c9', 'GESTION DE LA SECURITE',
        'GESTION DES RISQUES',
        'MAINTENANCE-GMAO', 'MAINTENANCE',
        'SECURITE', 'SECURITE ET SYSTEMES INFORMATIQUES',
        "STAGE D'IMMERSION",
    ],
}

# Construire un dict plat: matiere_upper → annee
_MATIERE_ANNEE_FLAT: Dict[str, int] = {}
for _annee, _matieres in MATIERE_ANNEE_MAP_RAW.items():
    for _m in _matieres:
        _MATIERE_ANNEE_FLAT[_m.strip().upper()] = _annee


async def fix_annee_etude_direct(standalone=False) -> tuple:
    """
    Corrige l'annee_etude de tous les documents en BD basé sur le nom de
    la matière — sans connexion à Google Drive. Utilise le mapping
    MATIERE_ANNEE_MAP_RAW défini dans ce fichier.
    """
    if standalone:
        try:
            await connect_db()
        except Exception:
            pass

    db = get_db()
    if db is None:
        return False, "Database not connected"

    docs_coll = db["documents"]
    total_updated = 0
    total_skipped_no_match = 0
    total_skipped_already = 0

    async for doc in docs_coll.find({}):
        matiere = (doc.get("matiere") or "").strip().upper()
        if not matiere:
            total_skipped_no_match += 1
            continue

        # Correspondance exacte
        annee = _MATIERE_ANNEE_FLAT.get(matiere)

        # Correspondance partielle si pas de correspondance exacte
        if annee is None:
            for key, val in _MATIERE_ANNEE_FLAT.items():
                if key in matiere or matiere in key:
                    annee = val
                    break

        if annee is None:
            total_skipped_no_match += 1
            print(f"  [?] Matière non reconnue: {matiere!r}")
            continue

        current = doc.get("annee_etude")
        if current == annee:
            total_skipped_already += 1
            continue

        await docs_coll.update_one(
            {"_id": doc["_id"]},
            {"$set": {"annee_etude": annee}}
        )
        total_updated += 1

    if standalone:
        try:
            await close_db()
        except Exception:
            pass

    return True, (
        f"Correction directe terminée. {total_updated} documents mis à jour. "
        f"{total_skipped_already} déjà corrects. "
        f"{total_skipped_no_match} matières non reconnues."
    )

if __name__ == "__main__":
    asyncio.run(sync_drive_to_db(standalone=True))

