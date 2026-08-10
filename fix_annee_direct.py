"""
Script de correction directe des annee_etude dans MongoDB.
Ce script assigne l'annee_etude aux documents basé sur les noms des matières
connues pour chaque cycle.

Pour un cycle EAC-SEI (exemple de répartition courante en école aéronautique):
- 1ère année: matières de base (électronique fondamentale, circuits électriques,
  mathématiques, physique, informatique de base, etc.)
- 2ème année: matières avancées (transmission, antennes, navigation, VOR, ILS,
  DME, GNSS, radar, etc.)
- 3ème année: matières de spécialisation (OIACM, SAAPI, SAOMA, surveillance, etc.)
"""
import asyncio
from database.db import connect_db, close_db, get_db

# Mapping des matières → année d'étude (EAC-SEI)
# Basé sur les noms de matières présents en base de données
# Ce mapping est une approximation qui devra être validée/ajustée
MATIERE_TO_ANNEE = {
    # === 1ère ANNÉE (fondamentaux) ===
    1: [
        'ELECTRONIQUE FONDAMENTALE', 'ELECTRONIQUE FONDAMENTALES', 'TP ELECTRONIQUE FONDAMENTALE',
        'CIRCUITS ELECTRIQUES', 'ELECTRICITE GENERAL',
        'MATHEMATIQUES', 'PHYSIQUE',
        'ALGORITHME ET PROGRAMMATION', "ALGORITHME ET PROGRAMMATION 'C'",
        'BUREAUTIQUE', 'INFORMATIQUE',
        'ANGLAIS GENERAL', 'Anglais general',
        'ANGLAIS TECHNIQUE', 'Anglais Technique', 'ANGLAIS TECHNIQUE ET PROFESSIONNEL',
        'SECOURISME',
        'REDACTION ADMINISTRATIVE', 'Redaction Administrative', 'RÉDACTION ADMINISTRATIVE', 'R\u00c9DACTION ADMINISTRATIVE',
        'AOP',
        'ELECTRONIQUE NUMERIQUE',
        'MICROPROCESSEUR-MICROCONTROLEUR', 'Microproceseur-Microcontrolleur', 'MICROPROCESSEUR-MICROCONTROLEUR',
        'MACHINE ELECTRIQUE',
        'ELECTRONIQUE DE PUISSANCE',
        'TECHNOLOGIES,MATERIELS ET COMPOSANTS ELECTRIQUES',
        'APPAREILS DE MESURE POUR ELECTRICIEN',
        'APPAREILS DE MESURE POUR ELECTRONICIEN',
        'MATERIEL ELECTRIQUE', 'Materiel Electrique',
        'ARCHITECTURE ET CONFIGURATION DES PC', 'Architechture et config PC',
        'FACTEURS HUMAINS',
        'GESTION DE CHANTIER ( CONDUITE ATTITUDE PREVENTION DES ACCIDENTS', 'Gestion de chantier',
        'Annexes',
        'logo',
    ],
    # === 2ème ANNÉE (transmission, navigation, radio) ===
    2: [
        'ANTENNES', 'Antennes',
        'EMISSION-RECEPTION', 'Emission Reception',
        'LIGNES ET HYPERFREQUENCES', 'Lignes et Hyperfrequences',
        'Propagation en espace libre',
        'VOR',
        'ILS',
        'DME',
        'GNSS', 'gnss',
        'NAVIGATION',
        'METEOROLOGIE',
        'ADS', 'ADS ALABE',
        'MULTILATERATION', 'mlat', 'MLAT',
        'BALISAGE LUMINEUX',
        'Chaine Radio',
        'Equipement VHF',
        'AEROTECHNIQUE',
        'COURS DE SAUVETAGE ET DE LUTTE  CONTRE L\'INCENDIE SUR LES AEROPORTS',
        'Faisceau Hertzien',
        'AUTOMATIQUE',
        'TECHNIQUES SATELLITAIRES', 'Technique Satellitaire',
        'TRANSMISSION DES DONNÉES', 'TRANSMISSION DES DONN\u00c9ES',
        'TRANSPORT DES DONNEES',
        'Radar MTO', 'RADIOSONDAGE', 'RadioSondage MTO', 'Radar M\u00e9t\u00e9o', 'RADAR METEO',
        'SYSTEME DE PRODUCTION ET DE GESTION D\'ENERGIE ELECTRIQUE',
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
        'INTRODUCTION AU RESEAU', 'Reseaux',
        'LES PROTOCOLES',
        'RESEAU NATIONAUX', 'RESEAUX INTERNATIONAUX',
        'BASE DE DONNEES',
        'SGBD',
        'SYS D\'EXPLOITATION ( LINUX-WINDOWS )',
        'SE Linux',
        'Pare-feu',
        'VPN',
        'Routeur',
        'TELEPHONIE', 'Telephonie',
        'Commutation Voix et donnees',
        'COMMUTATEUR DE MESSAGES',
        'SYST DE CHAINES DE RADIOTELEPHONIE ( VCCS )',
        'ETUDE DE MATERIELS-EQUIPMNTS VSAT ET ENERGIE',
        'ETUDES DE MATERIELS MULTIPLEXEURS ET COMMUTATEUR',
        'TRAITEMENT DE DONNEES DE SURVEILLANCE',
        'MULTILATERATION', 'mlat',
        'Radar de contr\u00f4le a\u00e9rien', 'Radar du controle aerien',
        'SYSTEME DE GESTION DE L\'INFORMATION AERONAUTIQUE',
        'GESTION DE LA S\u00c9CURIT\u00c9', 'GESTION DE LA SECURITE',
        'GESTION DES RISQUES',
        'MAINTENANCE-GMAO', 'Maintenance',
        'Securite', 'Securite et Systemes Informatiques',
        'Stage d\'immersion',
        'NAVIGATION',
    ],
}

# Construire un dictionnaire plat: matiere_lower -> annee
MATIERE_ANNEE_MAP = {}
for annee, matieres in MATIERE_TO_ANNEE.items():
    for m in matieres:
        MATIERE_ANNEE_MAP[m.strip().upper()] = annee


async def fix_annee_etude_direct():
    """
    Corrige l'annee_etude de tous les documents en BD
    basé sur le nom de la matière.
    """
    await connect_db()
    db = get_db()
    docs_coll = db["documents"]
    
    total = await docs_coll.count_documents({})
    updated = 0
    skipped_no_match = 0
    skipped_already_set = 0
    
    print(f"Total documents: {total}")
    print("Début de la correction...")
    
    async for doc in docs_coll.find({}):
        matiere = (doc.get("matiere") or "").strip().upper()
        
        if not matiere:
            skipped_no_match += 1
            continue
        
        # Chercher correspondance exacte d'abord
        annee = MATIERE_ANNEE_MAP.get(matiere)
        
        # Si pas de correspondance exacte, chercher si la matière contient un mot-clé
        if annee is None:
            for key, val in MATIERE_ANNEE_MAP.items():
                if key in matiere or matiere in key:
                    annee = val
                    break
        
        if annee is None:
            skipped_no_match += 1
            print(f"  [?] Matière non reconnue: {matiere!r}")
            continue
        
        # Ne mettre à jour que si annee_etude n'est pas déjà correct
        current = doc.get("annee_etude")
        if current == annee:
            skipped_already_set += 1
            continue
        
        await docs_coll.update_one(
            {"_id": doc["_id"]},
            {"$set": {"annee_etude": annee}}
        )
        updated += 1
    
    await close_db()
    print(f"\n=== RÉSULTAT ===")
    print(f"Mis à jour: {updated}")
    print(f"Déjà corrects: {skipped_already_set}")
    print(f"Matière non reconnue: {skipped_no_match}")
    print("Correction terminée.")

if __name__ == "__main__":
    asyncio.run(fix_annee_etude_direct())
