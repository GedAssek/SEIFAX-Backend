import json
import re

subjects = [
    {
        "cycle": "EAC1",
        "label": "IEAMAC EAC1 (1ère année)",
        "matieres": ["Introduction", "Généralités", "Contrôle d'aérodrome", "Infrastructure et Balisage", "BDP & SIA", "Organisation et Exploit. des Téléc, aéro et météo", "SFA", "Electromagnétisme", "Thermodynamique", "Mécanique quantique", "Mécanique des fluides", "Maths pour physique", "Algèbre", "Analyse", "Analyse numérique", "Probabilités", "Statistiques", "Introduction à l'algorithme et à la programmation (Langage C)", "Anglais général", "Anglais technique", "Aérodynamique", "Mécanique du vol", "Navigation aérienne", "OIACM", "Droit aérien", "Réglementation technique du transport aérien", "Météorologie générale", "Météorologie aéronautique", "Météorologie tropicale", "Identification avions", "Sûreté aéroportuaire", "Bureautique", "Electronique", "Antennes - Propagation", "Emission - Réception"]
    },
    {
        "cycle": "EAC2",
        "label": "IEAMAC EAC2 (2ème année)",
        "matieres": ["Contrôle d'approche", "Construction des procédures", "Contrôle en route", "Limites d'utilisation", "Méthodes d'exploitation", "SMA", "ATN", "Anglais général", "Anglais technique", "Avionique 1", "Avionique 2", "Econométrie", "Economie du transport aérien", "Langage C", "Système d'exploitation", "Téléinformatique", "Système de gestion des bases de données", "Circuits avions", "Cellule structure", "Propulsion", "Initiation au pilotage", "Installations électriques", "Enquêtes accidents", "Satellites de télécommunications", "Recherches et sauvetage", "SSLI", "Moyens de surveillance", "Radionavigation", "Logique", "Automatique", "Microéconomie", "Macroéconomie", "Gestion financière", "Administration des entreprises", "Initiation au droit", "Etude de contrat", "Electrotechnique", "Secourisme"]
    },
    {
        "cycle": "EAC3",
        "label": "IEAMAC EAC3 (3ème année)",
        "matieres": ["Méthodologie de planification de l'EA", "Projet OPS/INFRA", "Gestion technique des aéroports", "Gestion commerciale des aéroports", "Anglais Professionnel", "Projet Economie du transport aérien", "Méthodologie de la programmation", "Système de gestion de la sécurité", "Système de gestion de la qualité", "CNS/ATM", "Analyse des données", "Recherches opérationnelles", "Calcul économique", "Gestion budgétaire de l'ASECNA", "Rédaction administrative", "Communication et techniques d'expression", "Facteurs Humains"]
    },
    {
        "cycle": "EAC/CA-AIM-TEL-TA",
        "label": "EAC/CA - AIM - TEL - TA (1ère & 2ème année)",
        "matieres": ["RCA Généralités", "Bureau de Piste", "Service de l'information aéronautique", "Infrastructure aéroportuaire et balisage", "Aérodynamique", "Mécanique du vol", "Circuits et cellule structure", "Propulsion", "Radionavigation", "Navigation Aérienne", "Organisation et exploitation des télécommunications", "Service mobile aéronautique", "Service fixe aéronautique", "Anglais Général", "Anglais Technique", "Maths/Algèbre", "Maths/Analyse", "Probabilités", "Statistiques", "Physique", "Bureautique", "Technologie des ordinateurs", "Administration de bases de données", "Introduction Algorithmique et programmation", "Gestion de la sécurité 1", "SMQ", "Economie du transport aérien", "Droit aérien", "Organisme internationaux (Aviation civile et Météo)", "Caractéristiques et performances des aéronefs", "Simulateur de vol/Pilotage", "Météorologie Générale", "Météorologie Aéronautique", "Secourisme", "Droit public", "Rédaction administrative", "Techniques de communication", "Techniques d'expression", "RCA Contrôle d'Aérodrome", "Gestion de la sécurité 2", "Avionique 1", "Enquêtes / Accidents Avion", "Facteurs Humains", "Gestion Technique des aéroports", "Gestion Commerciale des aéroports", "Sûreté aéroportuaire", "Sauvetage et lutte contre l'incendie (SLI)", "Recherche et sauvetage", "Administration des entreprises"]
    },
    {
        "cycle": "EAC/CA-OPT",
        "label": "EAC/CA Option Circulation Aérienne",
        "matieres": ["RCA Contrôle d'approche", "RCA Contrôle en route", "PANS/OPS", "CNS/ATM", "Réglementation du transport aérien", "Opérations aériennes (LU et TU)", "Exploitation radar", "Exploitation ADS", "Moyens de surveillance (Radar - ADS - MLAT)"]
    },
    {
        "cycle": "EAC/AIM-OPT",
        "label": "EAC/AIM Option Gestion Information Aéronautique",
        "matieres": ["RCA Contrôle d'approche", "PANS/OPS", "CNS/ATM", "Réglementation du transport aérien", "Opérations aériennes (LU et TU)", "Exploitation BDP/SIA", "Cartographie aéronautique", "Système WGS 84", "Système d'information géographique", "Cartographie d'aérodrome", "SMQ AIM", "Réseaux informatiques et télécom", "Administration réseau", "Moyens de surveillance"]
    },
    {
        "cycle": "EAC/TEL-OPT",
        "label": "EAC/TEL Option Télécommunications",
        "matieres": ["Acheminement OACI", "Acheminement OMM", "Messages de service", "SMT", "TP des télécommunications", "Réseaux informatiques et télécom", "Logique", "Administration réseau", "Antennes - Propagation", "Emission / Réception", "CNS/ATM", "Moyens de surveillance", "Format IWXXM (XML/GML)", "Télécommunications par satellites", "Réseaux de télécommunications aéronautiques (ATN)", "Formes symboliques des messages d'observation météorologiques", "Procédures de contrôle des OPMET en région AFI", "Procédures de contrôle de l'OMM", "Gestion du spectre des radiofréquences aéronautiques"]
    },
    {
        "cycle": "EAC/ET",
        "label": "EAC/ET (Tronc commun & Options)",
        "matieres": ["RCA : Généralités", "RCA : Contrôle d'aérodrome", "BDP & SIA", "Infrastructures et balisage", "Télécommunications Généralités", "Service mobile aéronautique", "Service fixe aéronautique", "Anglais général", "Météorologie générale", "Météorologie aéronautique", "Aérotechnique", "Caractéristiques et performances avions", "Sûreté aéroportuaire", "Organismes internationaux de l'aviation civiles et de la météorologie", "Radionavigation/Systèmes de bord", "Navigation aérienne", "Réglementation technique du transport aérien", "Opérations aériennes", "Economie du transport aérien", "SSLI", "Gestion technique des aéroports", "Gestion commerciale des aéroports", "Gestion de la sécurité", "Maths : Statistiques/Probabilités", "Physiques", "Informatique (Système d'expl., Bureautique, Réseaux)", "Technique d'expression", "Secourisme", "Exploitation BDP/SIA (carto, AIS,FON,BDP)", "SMQ AIM", "Simulateur de vol/Pilotage", "SMT/SIO", "Acheminement OACI", "Acheminement OMM", "Réseaux de télécommunication (ATN)", "TP des télécommunications", "Messages de service", "Formes symboliques des messages météorologiques", "Procédure de contrôle des OPMET", "Procédure de contrôle OMM"]
    },
    {
        "cycle": "CCA",
        "label": "CCA (Aérodrome/Approche & En-route)",
        "matieres": ["RCA : Généralités", "RCA : Contrôle d'aérodrome", "Infrastructures aéroportuaires & balisage", "BDP & SIA", "RCA : Contrôle d'approche", "PANS/OPS (procédures IFR, RNAV/RNP)", "Exploitation radar", "Aérodynamique", "Mécanique du vol", "Circuits et cellule structure", "Propulsion", "Radionavigation", "Navigation", "Organisation et exploitation des télécommunications", "Service mobile aéronautique (SMA)", "Service fixe aéronautique (SFA)", "Anglais général", "Anglais technique", "SMQ", "Gestion de la sécurité 1", "Caractéristiques et Performances des avions", "Aéroport/environnement/risque animalier", "Gestion Technique des aéroports", "Gestion Commerciale des aéroports", "Sûreté aéroportuaire", "Sauvetage et lutte contre l'incendie", "Recherches et sauvetage", "Simulateur de vol/Pilotage", "Avionique", "Moyens de surveillance [Radar, ADS/CPDLC (terrestre et satellite)]", "OIACM", "Météo Générale", "Assistance météorologique à la NA", "Opérations aériennes: Limites d'utilisation", "Opérations aériennes: Méthodes d'exploitation", "Informatique: bureautique, système d'exploitation", "Droit aérien", "Droit du travail", "Droit: responsabilités civiles et pénales", "Facteurs humains", "Secourisme et hygiène du travail", "Techniques de communication", "RCA : Contrôle en route", "Exploitation ADS", "Gestion de la sécurité 2", "CNS/ATM", "Economie du Transport Aérien", "Réglementation technique du transport aérien", "Enquête Accident", "SGBD", "Programmation Langage C", "Informatique Réseaux", "Gestion budgétaire ASECNA", "Technique d'expression", "Rédaction administrative"]
    },
    {
        "cycle": "CCA-P",
        "label": "CCA-P & CCA-R (Perfectionnement & Recyclage)",
        "matieres": ["RCA : Généralités", "RCA : Contrôle d'aérodrome", "Infrastructures aéroportuaires & balisage", "BDP & SIA", "RCA : Contrôle d'approche", "PANS/OPS", "Exploitation radar", "Aérodynamique", "Mécanique du vol", "Circuits et cellule structure", "Propulsion", "Radionavigation", "Navigation", "Organisation et exploitation des télécommunications", "Service mobile aéronautique (SMA)", "Service fixe aéronautique (SFA)", "Anglais général", "Anglais technique", "SMQ", "Gestion de la sécurité 1", "Caractéristiques et Performances des avions", "Enquêtes Accident", "Aéroport/environnement/risque animalier", "Gestion Technique des aéroports", "Gestion Commerciale des aéroports", "Sûreté aéroportuaire", "Sauvetage et lutte contre l'incendie", "Recherches et sauvetage", "Simulateur de vol/Pilotage", "Avionique", "Moyens de surveillance", "OIACM", "Météo Générale", "Assistance météorologique à la NA", "Opérations aériennes: Limites d'utilisation", "Opérations aériennes: Méthodes d'exploitation", "Informatique: bureautique, système d'exploitation", "Droit aérien", "Droit du travail", "Droit: responsabilités civiles et pénales", "Facteurs humains", "Secourisme et hygiène du travail", "Techniques de communication", "RCA : Contrôle en route", "Exploitation ADS", "Gestion de la sécurité", "CNS/ATM", "Economie du Transport Aérien", "Réglementation technique du transport aérien", "Gestion budgétaire ASECNA", "Technique de comunication"]
    },
    {
        "cycle": "SEI",
        "label": "Ingénieurs Systèmes (IEAMAC/SEI1 & EI3)",
        "matieres": ["Circuits Electriques", "Electronique Fondamentale", "Microprocesseurs et Structure des calc.", "Intro à l'algorithmique et à la programmation", "Electronique Numérique", "Anglais Général", "Anglais technique et professionnel", "Maths pour physique", "Thermodynamique", "Vibrations", "Mécanique de fluide", "Mathématiques Analyse", "Mathématiques Algèbre", "Probabilités", "Systèmes Linéaires continus", "Système linéaires échantillonnés", "Bureautique", "Organisations et Normes internationaux", "Poste et milieu de travail", "Protection de l'environnement", "Sécurité personnelle", "Circulation aérienne", "Aérotechnique", "Météorologie", "Sécurité incendie", "Communications et Réseaux ATM", "Navigation", "Surveillance", "Moyens et installations", "Secourisme", "Introduction aux Réseaux", "Les réseaux nationaux", "Les réseaux internationaux", "Les réseaux mondiaux", "Les protocoles", "Statistiques", "Recherche Opérationnelle", "Analyse Numérique", "Macro-économie", "Transmissions numériques", "Radionavigation", "Radar", "Antennes", "Propagation réelle", "Télécommunications par satellites", "Faisceaux hertziens", "Méthodologie et conception des logiciels", "Maintenance", "Introduction CNS/ATM", "GNSS", "Communications ATN", "Multilatération", "Equipements MTO satellitaires", "Anglais technique", "Gestion budgétaire ASECNA", "Rédaction administrative", "Gestion financière", "Calcul économique", "Droit public", "Analyse des données", "Simulateur de vol", "Communication et technique d'expression", "Gestion de projet", "Gestion des ressources humaines", "SMQ / SGS", "Electricité générale", "Programmation C", "Technologies, Matières et Composants électroniques", "Appareils de mesure et outillage pour électronicien", "Amplificateur opérationnel", "Machines électriques", "Electronique de puissance", "Automatique", "Organisations et Normes", "Transmission de données", "Commutateur de messages", "Systèmes de gestion de l'information aéronautique", "Traitement de données de surveillance", "Transport d'énergie électrique", "Transport de données", "Système de production et de gestion énergie", "Balisage"]
    }
]

# Update Frontend api.js
api_path = r"c:\Users\AYENA Gédéon\OneDrive\Desktop\SEIFAX\Frontend\js\api.js"
with open(api_path, "r", encoding="utf-8") as f:
    api_content = f.read()

json_str = json.dumps(subjects, indent=4, ensure_ascii=False)
new_api_content = re.sub(r"const SUBJECTS_DATA = \[.*?\];", f"const SUBJECTS_DATA = {json_str};", api_content, flags=re.DOTALL)

with open(api_path, "w", encoding="utf-8") as f:
    f.write(new_api_content)


# Update Backend seed.py
seed_path = r"c:\Users\AYENA Gédéon\OneDrive\Desktop\SEIFAX\Backend\seed.py"
with open(seed_path, "r", encoding="utf-8") as f:
    seed_content = f.read()

new_seed_content = re.sub(r"SUBJECTS_DATA = \[.*?\]\n\n\nUSERS_DATA = \[", f"SUBJECTS_DATA = {json_str}\n\n\nUSERS_DATA = [", seed_content, flags=re.DOTALL)

with open(seed_path, "w", encoding="utf-8") as f:
    f.write(new_seed_content)

print("Data successfully updated in api.js and seed.py")
