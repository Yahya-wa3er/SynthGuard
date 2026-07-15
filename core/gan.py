"""
SynthGuard — core/gan.py
=========================
Entraînement du CTGAN conditionnel pour la génération
d'anomalies synthétiques réalistes par type.

Auteur  : El Houti Tlemcani Yahya
Projet  : SynthGuard — Détection d'anomalies B2B
Semaine : S5
"""

import numpy as np
import pandas as pd
import joblib
import os
import time
import json
import warnings
warnings.filterwarnings("ignore")

from sdv.single_table  import CTGANSynthesizer
from sdv.metadata      import SingleTableMetadata
from sdv.sampling      import Condition
from sqlalchemy        import create_engine, text

# ═══════════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

RANDOM_SEED   = 42
ARTIFACTS     = "../artifacts"
MODELS_DIR    = "../models"
os.makedirs(MODELS_DIR, exist_ok=True)

DB_URL        = "postgresql://user:password@localhost:5432/synthguard"

# Nombre d'anomalies synthétiques à générer par type
N_SYNTH_PER_TYPE = 1_250
N_TYPES          = 4
N_SYNTH_TOTAL    = N_SYNTH_PER_TYPE * N_TYPES   # 5 000

# Hyperparamètres CTGAN
CTGAN_EPOCHS      = 300
CTGAN_BATCH_SIZE  = 256
CTGAN_GENERATOR   = (256, 256)    # couches du générateur
CTGAN_DISCRIMIN   = (256, 256)    # couches du discriminateur
PAC               = 1            # Pac parameter (stabilité GAN)

# Labels des 4 types d'anomalies
ANOMALY_TYPES = {
    1: "coquille_vide",
    2: "outlier_sectoriel",
    3: "filiale_fantome",
    4: "saisie_aberrante",
}

np.random.seed(RANDOM_SEED)

print("=" * 65)
print("  SynthGuard — Entraînement CTGAN")
print("=" * 65)
print(f"  Anomalies réelles   : données du train set")
print(f"  Anomalies à générer : {N_SYNTH_TOTAL:,} ({N_SYNTH_PER_TYPE} par type)")
print(f"  Epochs CTGAN        : {CTGAN_EPOCHS}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CHARGEMENT ET PRÉPARATION DES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1/4] Préparation des données...")

# Charger les splits de S2
X_train = np.load(f"{ARTIFACTS}/X_train.npy").astype(np.float32)
y_train = np.load(f"{ARTIFACTS}/y_train.npy")
feature_cols = joblib.load(f"{ARTIFACTS}/feature_cols.pkl")

print(f"    -> X_train chargé    : {X_train.shape}")
print(f"    -> Features          : {len(feature_cols)}")

# Extraire uniquement les anomalies du train set
X_anom = X_train[y_train == 1]
print(f"    -> Anomalies réelles : {X_anom.shape[0]:,} lignes")

# Reconstruire un DataFrame avec les noms de colonnes
df_anom = pd.DataFrame(X_anom, columns=feature_cols)

# ── Récupérer les types d'anomalies directement depuis PostgreSQL ────────────
# Option B : la colonne anomaly_type a été sauvegardée en S1
# C'est la source de vérité — aucune reconstruction approximative nécessaire

print("    -> Récupération des anomaly_type depuis PostgreSQL...")

engine_temp = create_engine(DB_URL, pool_pre_ping=True)
df_types = pd.read_sql(
    sql = text("SELECT id, anomaly_type FROM client_accounts WHERE label = 1 ORDER BY id"),
    con = engine_temp.connect()
)

# Reconstruire l'index pour alignement avec X_train
# Les anomalies dans X_train correspondent aux lignes label=1 de PostgreSQL
# dans le même ordre que le split de S2 (trié par id)
df_anom['anomaly_type'] = df_types['anomaly_type'].values[:len(df_anom)]

print(f"    -> anomaly_type récupéré pour {len(df_anom):,} anomalies")

# Rapport de répartition
print(f"\n    Répartition des types dans le train set :")
type_counts = df_anom['anomaly_type'].value_counts().sort_index()
for t, c in type_counts.items():
    print(f"       Type {t} ({ANOMALY_TYPES[t]:<22}) : {c:>5,} lignes")

# Vérifier que les 4 types sont représentés
missing = set(ANOMALY_TYPES.keys()) - set(type_counts.index)
if missing:
    print(f"    [!] Types manquants : {missing} — génération ignorée pour ces types")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ENTRAÎNEMENT CTGAN
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[2/4] Entraînement CTGAN ({CTGAN_EPOCHS} epochs)...")

# ── Métadonnées SDV ──────────────────────────────────────────────────────────
# SDV a besoin de connaître le type de chaque colonne
metadata = SingleTableMetadata()
metadata.detect_from_dataframe(df_anom)

# Forcer le type de la colonne conditionnelle en catégoriel
metadata.update_column(
    column_name = 'anomaly_type',
    sdtype      = 'categorical'
)

# Toutes les features normalisées sont numériques continues
for col in feature_cols:
    metadata.update_column(
        column_name = col,
        sdtype      = 'numerical'
    )

# ── Initialisation du CTGAN ──────────────────────────────────────────────────
synthesizer = CTGANSynthesizer(
    metadata            = metadata,
    enforce_min_max_values = False,   # on veut garder les valeurs hors [0,1]
                                      # pour les anomalies type 4
    enforce_rounding    = False,
    epochs              = CTGAN_EPOCHS,
    batch_size          = CTGAN_BATCH_SIZE,
    generator_dim       = CTGAN_GENERATOR,
    discriminator_dim   = CTGAN_DISCRIMIN,
    pac                 = PAC,
    verbose             = True,
)

t0 = time.time()
synthesizer.fit(df_anom)
elapsed = time.time() - t0

print(f"\n    CTGAN entraîné en {elapsed:.1f}s")

# Sauvegarde du synthesizer
synthesizer.save(f"{MODELS_DIR}/ctgan_synthesizer.pkl")
print(f"    -> Synthesizer sauvegardé : {MODELS_DIR}/ctgan_synthesizer.pkl")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GÉNÉRATION ET VALIDATION QUALITÉ
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[3/4] Génération et validation qualité...")

# ── Génération conditionnelle par type ───────────────────────────────────────
# On génère chaque type séparément pour un contrôle précis
synthetic_frames = []

for anomaly_type in sorted(ANOMALY_TYPES.keys()):

    if anomaly_type not in type_counts.index:
        print(f"    [!] Type {anomaly_type} absent — ignoré")
        continue

    print(f"\n    Génération Type {anomaly_type} ({ANOMALY_TYPES[anomaly_type]})...")

    # Générer avec condition sur le type
    condition = Condition(
        column_values = {'anomaly_type': anomaly_type},
        num_rows      = N_SYNTH_PER_TYPE,
    )
    df_synth_type = synthesizer.sample_from_conditions(
        conditions = [condition],
    )

    print(f"       Généré : {len(df_synth_type):,} lignes")

    # ── Validation statistique (comparaison réel vs synthétique) ────────────
    df_real_type = df_anom[df_anom['anomaly_type'] == anomaly_type][feature_cols]
    df_synt_feat = df_synth_type[feature_cols]

    print(f"       Validation statistique (features clés) :")
    validation_ok = True

    for col in ['revenue', 'employees', 'year_established']:
        if col not in feature_cols:
            continue
        real_mean = df_real_type[col].mean()
        synt_mean = df_synt_feat[col].mean()
        real_std  = df_real_type[col].std()
        synt_std  = df_synt_feat[col].std()

        # Critère : la moyenne synthétique ne doit pas dévier de plus de
        # 3 écarts-types par rapport à la moyenne réelle
        deviation = abs(synt_mean - real_mean) / (real_std + 1e-8)
        status = "✓" if deviation < 3 else "⚠"
        if deviation >= 3:
            validation_ok = False

        print(
            f"       {status} {col:<22} | "
            f"réel: mean={real_mean:.4f} std={real_std:.4f} | "
            f"synt: mean={synt_mean:.4f} std={synt_std:.4f} | "
            f"déviation: {deviation:.2f}σ"
        )

    if not validation_ok:
        print(f"       [!] Qualité dégradée sur type {anomaly_type} — données conservées mais à surveiller")

    synthetic_frames.append(df_synth_type)

# ── Assemblage final ─────────────────────────────────────────────────────────
df_synthetic = pd.concat(synthetic_frames, ignore_index=True)
print(f"\n    Total anomalies synthétiques générées : {len(df_synthetic):,}")

# Répartition finale
print(f"    Répartition finale :")
final_counts = df_synthetic['anomaly_type'].value_counts().sort_index()
for t, c in final_counts.items():
    print(f"       Type {t} ({ANOMALY_TYPES[t]:<22}) : {c:>5,}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SAUVEGARDE
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[4/4] Sauvegarde des artefacts...")

# ── Extraire uniquement les features (sans anomaly_type) ────────────────────
X_synthetic = df_synthetic[feature_cols].values.astype(np.float32)
y_synthetic = np.ones(len(X_synthetic), dtype=np.int8)   # label = 1

print(f"    -> X_synthetic shape : {X_synthetic.shape}")

# ── Dataset augmenté : train normal + vraies anomalies + anomalies GAN ───────
X_train_normal  = X_train[y_train == 0]
y_train_normal  = y_train[y_train == 0]
X_train_anomaly = X_train[y_train == 1]
y_train_anomaly = y_train[y_train == 1]

X_augmented = np.vstack([X_train_normal, X_train_anomaly, X_synthetic])
y_augmented = np.concatenate([y_train_normal, y_train_anomaly, y_synthetic])

# Shuffle
idx = np.random.permutation(len(X_augmented))
X_augmented = X_augmented[idx]
y_augmented = y_augmented[idx]

print(f"\n    Dataset augmenté (pour S7 — score hybride) :")
print(f"       Normaux             : {(y_augmented==0).sum():>8,}")
print(f"       Vraies anomalies    : {len(X_train_anomaly):>8,}")
print(f"       Anomalies GAN       : {len(X_synthetic):>8,}")
print(f"       Total               : {len(X_augmented):>8,}")
print(f"       % anomalies         : {(y_augmented==1).sum()/len(y_augmented)*100:.2f}%")

# ── Sauvegardes .npy ─────────────────────────────────────────────────────────
np.save(f"{ARTIFACTS}/X_synthetic.npy",   X_synthetic)
np.save(f"{ARTIFACTS}/y_synthetic.npy",   y_synthetic)
np.save(f"{ARTIFACTS}/X_augmented.npy",   X_augmented)
np.save(f"{ARTIFACTS}/y_augmented.npy",   y_augmented)

# ── Sauvegarde PostgreSQL ────────────────────────────────────────────────────
print(f"\n    Insertion dans PostgreSQL (table synthetic_anomalies)...")

df_to_db = df_synthetic[feature_cols].copy()
df_to_db['anomaly_type'] = df_synthetic['anomaly_type'].values
df_to_db['label']        = 1
df_to_db['source']       = 'ctgan'

engine = create_engine(DB_URL, pool_pre_ping=True)

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS synthetic_anomalies (
            id           SERIAL PRIMARY KEY,
            anomaly_type INTEGER,
            label        SMALLINT,
            source       TEXT,
            inserted_at  TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.commit()

df_to_db.to_sql(
    name      = 'synthetic_anomalies',
    con       = engine,
    if_exists = 'replace',
    index     = False,
    chunksize = 1_000,
    method    = 'multi',
)
print(f"    -> {len(df_to_db):,} lignes insérées dans synthetic_anomalies")

# ── Rapport JSON ─────────────────────────────────────────────────────────────
report = {
    "n_real_anomalies"   : int(len(X_train_anomaly)),
    "n_synthetic"        : int(len(X_synthetic)),
    "n_augmented_total"  : int(len(X_augmented)),
    "pct_anomalies"      : float((y_augmented==1).sum() / len(y_augmented) * 100),
    "ctgan_epochs"       : CTGAN_EPOCHS,
    "types_generated"    : {str(k): int(v) for k, v in final_counts.items()},
}

with open(f"{MODELS_DIR}/ctgan_report.json", "w") as f:
    json.dump(report, f, indent=2)

print(f"\n    Artefacts sauvegardés :")
for fname in ["X_synthetic.npy", "y_synthetic.npy", "X_augmented.npy", "y_augmented.npy"]:
    path = f"{ARTIFACTS}/{fname}"
    size = os.path.getsize(path) / 1024 / 1024
    print(f"    -> {fname:<30} {size:.1f} MB")
print(f"    -> {MODELS_DIR}/ctgan_synthesizer.pkl")
print(f"    -> {MODELS_DIR}/ctgan_report.json")

print("\n" + "=" * 65)
print("  CTGAN — Génération terminée")
print(f"  Anomalies synthétiques : {len(X_synthetic):,}")
print(f"  Dataset augmenté       : {len(X_augmented):,} lignes")
print(f"  Prêt pour S7 — Score hybride")
print("=" * 65)