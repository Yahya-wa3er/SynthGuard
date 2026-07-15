"""
SynthGuard — Script de génération du dataset synthétique
=========================================================
Génère 505 000 lignes (500 000 normales + 5 000 anomalies)
et les insère dans PostgreSQL via SQLAlchemy.

Auteur  : El Houti Tlemcani Yahya
Projet  : SynthGuard — Détection d'anomalies B2B
Version : 1.0
"""

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
import time

# ═══════════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION GLOBALE
# ═══════════════════════════════════════════════════════════════════════════════

RANDOM_SEED     = 42
N_NORMAL        = 500_000
N_ANOMALIES     = 5_000          # 1 250 par type
N_ANOMALY_TYPES = 4
N_PER_TYPE      = N_ANOMALIES // N_ANOMALY_TYPES   # 1 250 chacun

# Connexion PostgreSQL — adapter selon votre environnement
DB_URL = "postgresql://user:password@localhost:5432/synthguard"

# Taille des blocs pour l'insertion (optimisé mémoire)
INSERT_CHUNK = 10_000

np.random.seed(RANDOM_SEED)

print("=" * 65)
print("  SynthGuard — Génération du dataset synthétique")
print("=" * 65)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LISTES DE RÉFÉRENCE
# ═══════════════════════════════════════════════════════════════════════════════

# Noms d'entreprises réalistes pour le CRM
COMPANY_NAMES = [
    "Acme Corporation",   "Betatech Solutions",  "Nexus Consulting",
    "Apex Dynamics",      "Orion Systems",        "Vertex Partners",
    "Cascade Analytics",  "Meridian Group",       "Titan Software",
    "Solaris Ventures",   "Quantum Advisors",     "Prism Technologies",
    "Aurora Digital",     "Helix Strategies",     "Synapse Corp",
    "Cobalt Innovations", "Nebula Networks",      "Stratos Advisory",
    "Luminary Group",     "Pinnacle Consulting",
]

SECTORS = ['technolgy', 'medical', 'retail', 'software', 'entertainment']

# Poids sectoriels : tech et software dominent en consulting B2B
SECTOR_WEIGHTS = [0.30, 0.20, 0.20, 0.20, 0.10]

# Poids géographiques : 80% USA, 20% reste du monde
LOCATIONS = [
    "United States", "United Kingdom", "Germany", "France",
    "Canada",        "Australia",      "Kenya",   "Philippines",
    "Brazil",        "India",
]
LOCATION_WEIGHTS = [0.80, 0.04, 0.03, 0.03, 0.03, 0.02, 0.01, 0.01, 0.02, 0.01]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GÉNÉRATION DES DONNÉES NORMALES (label = 0)
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[1/4] Génération des {N_NORMAL:,} lignes normales...")
t0 = time.time()

# --- Année de création ---
# Distribution réaliste : majorité entre 1980-2015, queue vers 2023
year_established = np.random.choice(
    range(1950, 2024),
    size=N_NORMAL,
    p=np.array([
        # Croissance progressive des créations d'entreprises
        *[0.003] * 10,    # 1950-1959
        *[0.004] * 10,    # 1960-1969
        *[0.006] * 10,    # 1970-1979
        *[0.010] * 10,    # 1980-1989
        *[0.016] * 10,    # 1990-1999
        *[0.020] * 10,    # 2000-2009
        *[0.025] * 10,    # 2010-2019
        *[0.020] * 4,     # 2020-2023 (léger recul post-COVID)
    ]) / sum([
        *[0.003] * 10, *[0.004] * 10, *[0.006] * 10,
        *[0.010] * 10, *[0.016] * 10, *[0.020] * 10,
        *[0.025] * 10, *[0.020] * 4,
    ])   # normalisation à 1
)

# --- Corrélation ancienneté → taille ---
# Plus l'entreprise est ancienne, plus elle est grande
# Age en années (référence : 2025)
age = 2025 - year_established   # entre 2 et 75 ans

# Nombre d'employés : croît avec l'âge (bruit log-normal)
employee_base   = 50 + age * 35          # base linéaire avec l'âge
employee_noise  = np.random.lognormal(0, 0.6, N_NORMAL)
employees       = np.maximum(1, (employee_base * employee_noise).astype(int))

# Revenue : corrélé aux employés + âge (bruit multiplicatif)
revenue_base   = 0.5 * employees + age * 8
revenue_noise  = np.random.lognormal(0, 0.5, N_NORMAL)
revenue        = np.maximum(0.01, revenue_base * revenue_noise).round(2)

# --- Secteur (pondéré) ---
sector = np.random.choice(SECTORS, size=N_NORMAL, p=SECTOR_WEIGHTS)

# --- Localisation (80% USA) ---
office_location = np.random.choice(
    LOCATIONS, size=N_NORMAL, p=LOCATION_WEIGHTS
)

# --- Noms d'entreprises (tirés de la liste + suffixe unique) ---
base_names  = np.random.choice(COMPANY_NAMES, size=N_NORMAL)
suffixes    = np.arange(N_NORMAL)
account     = np.array([f"{n} #{i}" for n, i in zip(base_names, suffixes)])

# --- subsidiary_of : 15% ont une maison mère ---
subsidiary_mask = np.random.rand(N_NORMAL) < 0.15
parent_pool     = np.random.choice(COMPANY_NAMES, size=N_NORMAL)
parent_pool_obj = parent_pool.astype(object)
subsidiary_of   = np.where(subsidiary_mask, parent_pool_obj, None)
# Convertir "nan" string en None proprement

# --- Assemblage du DataFrame normal ---
df_normal = pd.DataFrame({
    "account"         : account,
    "sector"          : sector,
    "year_established": year_established,
    "revenue"         : revenue,
    "employees"       : employees,
    "office_location" : office_location,
    "subsidiary_of"   : subsidiary_of,
    "label"           : 0,
    "anomaly_type"    : 0,
})

print(f"    -> {len(df_normal):,} lignes normales générées en {time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GÉNÉRATION DES ANOMALIES (label = 1)
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[2/4] Génération des {N_ANOMALIES:,} anomalies ({N_PER_TYPE} par type)...")

anomaly_frames = []

# ─────────────────────────────────────────────────────────────────────────────
# TYPE 1 : Coquilles vides frauduleuses
# Logique : entreprises toutes neuves (>= 2025), quasi pas d'employés,
#           mais revenue astronomique → fraude / blanchiment / erreur CRM
# ─────────────────────────────────────────────────────────────────────────────
print("    -> Type 1 : Coquilles vides frauduleuses...")

t1_year      = np.random.choice(range(2025, 2031), size=N_PER_TYPE)
t1_employees = np.random.randint(1, 6, size=N_PER_TYPE)           # 1 à 5
t1_revenue   = np.random.uniform(15_000, 50_000, size=N_PER_TYPE).round(2)
t1_sector    = np.random.choice(SECTORS, size=N_PER_TYPE, p=SECTOR_WEIGHTS)
t1_location  = np.random.choice(LOCATIONS, size=N_PER_TYPE, p=LOCATION_WEIGHTS)
t1_names     = np.array([f"Shell Corp T1 #{i}" for i in range(N_PER_TYPE)])

df_t1 = pd.DataFrame({
    "account"         : t1_names,
    "sector"          : t1_sector,
    "year_established": t1_year,
    "revenue"         : t1_revenue,
    "employees"       : t1_employees,
    "office_location" : t1_location,
    "subsidiary_of"   : np.nan,
    "label"           : 1,
    "anomaly_type"    : 1,
})
anomaly_frames.append(df_t1)

# ─────────────────────────────────────────────────────────────────────────────
# TYPE 2 : Outliers sectoriels
# Logique : retail / entertainment avec métriques de géant tech —
#           impossible dans la normalité → le VAE/CTGAN doit apprendre
#           la distribution conditionnelle secteur → revenue
# ─────────────────────────────────────────────────────────────────────────────
print("    -> Type 2 : Outliers sectoriels...")

t2_sector    = np.random.choice(['retail', 'entertainment'], size=N_PER_TYPE)
t2_revenue   = np.random.uniform(80_000, 200_000, size=N_PER_TYPE).round(2)
t2_employees = np.random.randint(30_001, 150_000, size=N_PER_TYPE)
t2_year      = np.random.choice(range(1990, 2015), size=N_PER_TYPE)
t2_location  = np.random.choice(LOCATIONS, size=N_PER_TYPE, p=LOCATION_WEIGHTS)
t2_names     = np.array([f"Sector Outlier T2 #{i}" for i in range(N_PER_TYPE)])

df_t2 = pd.DataFrame({
    "account"         : t2_names,
    "sector"          : t2_sector,
    "year_established": t2_year,
    "revenue"         : t2_revenue,
    "employees"       : t2_employees,
    "office_location" : t2_location,
    "subsidiary_of"   : np.nan,
    "label"           : 1,
    "anomaly_type"    : 2,
})
anomaly_frames.append(df_t2)

# ─────────────────────────────────────────────────────────────────────────────
# TYPE 3 : Incohérence Filiale (Subsidiary Mismatch)
# Logique : rattachée à un grand groupe MAIS revenue ≈ 0 et 1 seul employé →
#           filiale fantôme ou erreur relationnelle CRM critique
# ─────────────────────────────────────────────────────────────────────────────
print("    -> Type 3 : Incohérence filiale...")

t3_parent    = np.random.choice(COMPANY_NAMES, size=N_PER_TYPE)
t3_revenue   = np.random.uniform(0.01, 0.10, size=N_PER_TYPE).round(4)
t3_employees = np.ones(N_PER_TYPE, dtype=int)                      # toujours 1
t3_year      = np.random.choice(range(2000, 2024), size=N_PER_TYPE)
t3_sector    = np.random.choice(SECTORS, size=N_PER_TYPE, p=SECTOR_WEIGHTS)
t3_location  = np.random.choice(LOCATIONS, size=N_PER_TYPE, p=LOCATION_WEIGHTS)
t3_names     = np.array([f"Ghost Sub T3 #{i}" for i in range(N_PER_TYPE)])

df_t3 = pd.DataFrame({
    "account"         : t3_names,
    "sector"          : t3_sector,
    "year_established": t3_year,
    "revenue"         : t3_revenue,
    "employees"       : t3_employees,
    "office_location" : t3_location,
    "subsidiary_of"   : t3_parent,
    "label"           : 1,
    "anomaly_type"    : 3,
})
anomaly_frames.append(df_t3)

# ─────────────────────────────────────────────────────────────────────────────
# TYPE 4 : Anomalies extrêmes de saisie (valeurs mathématiquement aberrantes)
# Logique : revenue négatif, année dans le futur lointain, employés négatifs →
#           erreurs critiques de saisie / injection CRM
# Répartis en 3 sous-types pour couvrir les 3 cas
# ─────────────────────────────────────────────────────────────────────────────
print("    -> Type 4 : Anomalies extrêmes de saisie...")

n_sub = N_PER_TYPE // 3      # ~416 chacun
n_rem = N_PER_TYPE - 3 * n_sub  # reste pour arrondi

# Sous-type 4a : revenue négatif
t4a_revenue   = np.random.uniform(-50_000, -0.01, size=n_sub).round(2)
t4a_employees = np.random.randint(10, 500, size=n_sub)
t4a_year      = np.random.choice(range(1990, 2024), size=n_sub)

# Sous-type 4b : année de création dans le futur (2030-2050)
t4b_revenue   = np.random.uniform(100, 5_000, size=n_sub).round(2)
t4b_employees = np.random.randint(5, 200, size=n_sub)
t4b_year      = np.random.choice(range(2030, 2051), size=n_sub)

# Sous-type 4c : nombre d'employés négatif
t4c_revenue   = np.random.uniform(50, 3_000, size=n_sub + n_rem).round(2)
t4c_employees = np.random.randint(-5_000, 0, size=n_sub + n_rem)
t4c_year      = np.random.choice(range(1990, 2024), size=n_sub + n_rem)

# Assemblage type 4
t4_revenue   = np.concatenate([t4a_revenue,   t4b_revenue,   t4c_revenue])
t4_employees = np.concatenate([t4a_employees, t4b_employees, t4c_employees])
t4_year      = np.concatenate([t4a_year,      t4b_year,      t4c_year])
t4_sector    = np.random.choice(SECTORS, size=N_PER_TYPE, p=SECTOR_WEIGHTS)
t4_location  = np.random.choice(LOCATIONS, size=N_PER_TYPE, p=LOCATION_WEIGHTS)
t4_names     = np.array([f"Bad Entry T4 #{i}" for i in range(N_PER_TYPE)])

df_t4 = pd.DataFrame({
    "account"         : t4_names,
    "sector"          : t4_sector,
    "year_established": t4_year,
    "revenue"         : t4_revenue,
    "employees"       : t4_employees,
    "office_location" : t4_location,
    "subsidiary_of"   : np.nan,
    "label"           : 1,
    "anomaly_type"    : 4,
})
anomaly_frames.append(df_t4)

# --- Assemblage de toutes les anomalies ---
df_anomalies = pd.concat(anomaly_frames, ignore_index=True)
print(f"    -> {len(df_anomalies):,} anomalies générées")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. FUSION, SHUFFLE ET VÉRIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[3/4] Fusion, shuffle et vérifications...")

# Concaténation normale + anomalies
df_final = pd.concat([df_normal, df_anomalies], ignore_index=True)

# Shuffle complet — simule un flux continu réaliste
df_final = df_final.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

# Vérifications de cohérence
assert len(df_final) == N_NORMAL + N_ANOMALIES, "Volume total incorrect"
assert df_final['label'].value_counts()[0] == N_NORMAL,    "Compte normaux incorrect"
assert df_final['label'].value_counts()[1] == N_ANOMALIES, "Compte anomalies incorrect"

# Rapport de validation
print(f"\n    Rapport de validation du dataset :")
print(f"    {'─'*45}")
print(f"    Volume total         : {len(df_final):>10,} lignes")
print(f"    Lignes normales      : {df_final['label'].value_counts()[0]:>10,} ({df_final['label'].value_counts()[0]/len(df_final)*100:.2f}%)")
print(f"    Lignes anomalies     : {df_final['label'].value_counts()[1]:>10,} ({df_final['label'].value_counts()[1]/len(df_final)*100:.2f}%)")
print(f"    Colonnes             : {list(df_final.columns)}")
print(f"    Valeurs NaN (sub.)   : {df_final['subsidiary_of'].isna().sum():>10,}")
print(f"\n    Distribution secteurs (normaux) :")
sector_dist = df_final[df_final['label']==0]['sector'].value_counts()
for s, c in sector_dist.items():
    print(f"      {s:<15} : {c:>8,}  ({c/N_NORMAL*100:.1f}%)")

print(f"\n    Distribution anomalies par type :")
for i, name in enumerate([
    "Type 1 - Coquilles",
    "Type 2 - Outliers sect.",
    "Type 3 - Filiales",
    "Type 4 - Saisies erronees"
], 1):
    count = [N_PER_TYPE, N_PER_TYPE, N_PER_TYPE, N_PER_TYPE][i-1]
    print(f"      {name:<28} : {count:>6,}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INSERTION DANS POSTGRESQL
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[4/4] Insertion dans PostgreSQL ({INSERT_CHUNK:,} lignes/bloc)...")
t_insert = time.time()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,     # vérifie la connexion avant chaque opération
    pool_recycle=3600,      # recycle les connexions toutes les heures
)

# Supprimer et recréer la table proprement à chaque exécution
# On ne laisse pas pandas gérer le schéma (il ne crée pas SERIAL ni les types corrects)
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS client_accounts"))
    conn.execute(text("""
        CREATE TABLE client_accounts (
            id                SERIAL PRIMARY KEY,
            account           TEXT,
            sector            TEXT,
            year_established  INTEGER,
            revenue           DOUBLE PRECISION,
            employees         INTEGER,
            office_location   TEXT,
            subsidiary_of     TEXT,
            label             SMALLINT,
            anomaly_type      SMALLINT DEFAULT 0,
            inserted_at       TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.commit()
    print("    -> Table 'client_accounts' recréée proprement")

# Insertion par blocs — if_exists='append' car la table existe déjà
df_final.to_sql(
    name       = "client_accounts",
    con        = engine,
    if_exists  = "append",         # table déjà créée manuellement ci-dessus
    index      = False,            # ne pas insérer l'index pandas
    chunksize  = INSERT_CHUNK,     # blocs de 10 000 lignes
    method     = "multi",          # insertion multi-valeurs (plus rapide)
)

elapsed = time.time() - t_insert
print(f"    -> {len(df_final):,} lignes insérées en {elapsed:.1f}s")
print(f"    -> Débit moyen : {len(df_final)/elapsed:,.0f} lignes/seconde")

# ── Vérification post-insertion ─────────────────────────────────────────────
with engine.connect() as conn:
    total_db   = conn.execute(text("SELECT COUNT(*) FROM client_accounts")).scalar()
    normal_db  = conn.execute(text("SELECT COUNT(*) FROM client_accounts WHERE label = 0")).scalar()
    anomaly_db = conn.execute(text("SELECT COUNT(*) FROM client_accounts WHERE label = 1")).scalar()

print(f"\n    Verification post-insertion :")
print(f"    Total en DB    : {total_db:>10,}")
print(f"    Normaux en DB  : {normal_db:>10,}")
print(f"    Anomalies en DB: {anomaly_db:>10,}")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. CREATION DES INDEX POUR KAFKA CONNECT
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[Bonus] Création des index pour Kafka Connect...")

with engine.connect() as conn:
    # Index sur l'ID (utilisé par Kafka Connect en mode incrementing)
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_client_accounts_id
        ON client_accounts(id)
    """))
    # Index sur le label pour les requêtes analytiques
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_client_accounts_label
        ON client_accounts(label)
    """))
    # Index sur le secteur pour les queries conditionnelles
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_client_accounts_sector
        ON client_accounts(sector)
    """))
    conn.commit()

print("    -> Index créés : id, label, sector")

print("\n" + "=" * 65)
print("  SynthGuard — Dataset généré avec succès")
print(f"  Total : {len(df_final):,} lignes dans PostgreSQL")
print(f"  Table : client_accounts")
print("=" * 65)