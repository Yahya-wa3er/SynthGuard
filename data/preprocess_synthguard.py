"""
SynthGuard — Pipeline de Prétraitement
=======================================
Lit les données depuis PostgreSQL, applique le nettoyage,
l'encodage, la normalisation et génère les splits train/val/test.

Auteur  : El Houti Tlemcani Yahya
Projet  : SynthGuard — Détection d'anomalies B2B
Version : 1.0
"""

import numpy as np
import pandas as pd
import joblib
import os
import time

from sqlalchemy            import create_engine, text
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# ═══════════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

RANDOM_SEED = 42
DB_URL      = "postgresql://user:password@localhost:5432/synthguard"

# Dossier de sortie pour les artefacts (scaler + datasets)
OUTPUT_DIR  = "../artifacts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Splits : 80% train / 10% val / 10% test
TRAIN_RATIO = 0.80
VAL_RATIO   = 0.10
TEST_RATIO  = 0.10

np.random.seed(RANDOM_SEED)

print("=" * 65)
print("  SynthGuard — Pipeline de Prétraitement")
print("=" * 65)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LECTURE DEPUIS POSTGRESQL
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1/6] Lecture des données depuis PostgreSQL...")
t0 = time.time()

engine = create_engine(DB_URL, pool_pre_ping=True)

df = pd.read_sql(
    sql = text("SELECT * FROM client_accounts ORDER BY id"),
    con = engine.connect()
)

print(f"    -> {len(df):,} lignes chargées en {time.time()-t0:.1f}s")
print(f"    -> Colonnes : {list(df.columns)}")
print(f"    -> Normales : {(df.label==0).sum():,} | Anomalies : {(df.label==1).sum():,}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. NETTOYAGE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[2/6] Nettoyage...")

# Supprimer les colonnes non utiles pour le modèle
# 'account' est un identifiant texte libre, 'id' est la clé primaire
# 'inserted_at' est un timestamp technique
cols_to_drop = [c for c in ['id', 'account', 'inserted_at'] if c in df.columns]
df.drop(columns=cols_to_drop, inplace=True)
print(f"    -> Colonnes supprimées : {cols_to_drop}")

# Supprimer les doublons
n_before = len(df)
df.drop_duplicates(inplace=True)
print(f"    -> Doublons supprimés : {n_before - len(df)}")

# Vérifier les valeurs manquantes
print(f"    -> Valeurs manquantes par colonne :")
for col in df.columns:
    n_null = df[col].isna().sum()
    if n_null > 0:
        print(f"       {col:<25} : {n_null:>8,} NaN")

# subsidiary_of : colonne relationnelle — on crée un flag binaire
# (1 = a une maison mère, 0 = entité indépendante)
# La valeur texte elle-même n'est pas utile pour le VAE
df['has_subsidiary'] = df['subsidiary_of'].notna().astype(int)
df.drop(columns=['subsidiary_of'], inplace=True)
print(f"    -> 'subsidiary_of' converti en flag binaire 'has_subsidiary'")

print(f"    -> Shape après nettoyage : {df.shape}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GESTION DES VALEURS MANQUANTES RÉSIDUELLES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3/6] Gestion des valeurs manquantes résiduelles...")

# Variables numériques → médiane
num_cols = ['year_established', 'revenue', 'employees']
for col in num_cols:
    n_null = df[col].isna().sum()
    if n_null > 0:
        median_val = df[col].median()
        df[col].fillna(median_val, inplace=True)
        print(f"    -> {col} : {n_null} NaN remplacés par médiane ({median_val:.2f})")

# Variables catégorielles → mode
cat_cols = ['sector', 'office_location']
for col in cat_cols:
    n_null = df[col].isna().sum()
    if n_null > 0:
        mode_val = df[col].mode()[0]
        df[col].fillna(mode_val, inplace=True)
        print(f"    -> {col} : {n_null} NaN remplacés par mode ({mode_val})")

print(f"    -> Valeurs manquantes résiduelles : {df.isna().sum().sum()}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ENCODAGE ONE-HOT DES VARIABLES CATÉGORIELLES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4/6] Encodage One-Hot...")

# Séparer label avant encodage pour ne pas l'altérer
labels = df['label'].copy()
df.drop(columns=['label'], inplace=True)

# One-Hot Encoding sur sector et office_location
# drop_first=False : on garde toutes les colonnes pour le VAE
#   (pas de problème de multicolinéarité pour les réseaux de neurones)
df_encoded = pd.get_dummies(
    df,
    columns       = ['sector', 'office_location'],
    drop_first    = False,
    dtype         = float
)

# Remettre le label
df_encoded['label'] = labels.values

print(f"    -> Shape avant encodage : {df.shape}")
print(f"    -> Shape après encodage : {df_encoded.shape}")
print(f"    -> Nouvelles colonnes créées :")
new_cols = [c for c in df_encoded.columns if c.startswith('sector_') or c.startswith('office_')]
for c in new_cols:
    print(f"       {c}")

# Sauvegarder la liste des colonnes features pour la production
feature_cols = [c for c in df_encoded.columns if c != 'label']
joblib.dump(feature_cols, f"{OUTPUT_DIR}/feature_cols.pkl")
print(f"\n    -> Liste des features sauvegardée : {OUTPUT_DIR}/feature_cols.pkl")
print(f"    -> Nombre total de features : {len(feature_cols)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. NORMALISATION MIN-MAX
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[5/6] Normalisation Min-Max...")

# Séparer features et labels
X = df_encoded[feature_cols].values.astype(np.float32)
y = df_encoded['label'].values.astype(np.int8)

# IMPORTANT : le scaler est fitté UNIQUEMENT sur les données normales
# pour ne pas que les anomalies influencent les bornes min/max
X_normal = X[y == 0]

scaler = MinMaxScaler(feature_range=(0, 1))
scaler.fit(X_normal)

# Transformer tout le dataset avec le scaler appris sur les normaux
X_scaled = scaler.transform(X)

# Clip entre 0 et 1 pour les anomalies qui dépassent les bornes
# (c'est voulu : les anomalies type 4 auront des valeurs < 0 ou > 1,
#  ce qui les rend encore plus détectables par le VAE)
# On NE clippe PAS intentionnellement pour préserver ce signal

print(f"    -> Scaler fitté sur {X_normal.shape[0]:,} données normales")
print(f"    -> Features min après scaling (normaux) : {X_scaled[y==0].min():.4f}")
print(f"    -> Features max après scaling (normaux) : {X_scaled[y==0].max():.4f}")
print(f"    -> Features min après scaling (anomalies) : {X_scaled[y==1].min():.4f}")
print(f"    -> Features max après scaling (anomalies) : {X_scaled[y==1].max():.4f}")

# Sauvegarder le scaler — CRITIQUE pour la production
joblib.dump(scaler, f"{OUTPUT_DIR}/scaler.pkl")
print(f"\n    -> Scaler sauvegardé : {OUTPUT_DIR}/scaler.pkl")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SPLIT TRAIN / VAL / TEST
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[6/6] Split Train / Val / Test...")

# Split 1 : extraire le test set (10%)
X_trainval, X_test, y_trainval, y_test = train_test_split(
    X_scaled, y,
    test_size    = TEST_RATIO,
    random_state = RANDOM_SEED,
    stratify     = y           # conserver la proportion anomalies/normaux
)

# Split 2 : extraire le val set depuis train+val (10% du total = ~11.1% du restant)
val_ratio_adjusted = VAL_RATIO / (TRAIN_RATIO + VAL_RATIO)
X_train, X_val, y_train, y_val = train_test_split(
    X_trainval, y_trainval,
    test_size    = val_ratio_adjusted,
    random_state = RANDOM_SEED,
    stratify     = y_trainval
)

# Rapport des splits
print(f"\n    {'Split':<12} {'Total':>10} {'Normaux':>10} {'Anomalies':>10} {'% anomalies':>12}")
print(f"    {'─'*55}")
for name, X_s, y_s in [
    ("Train",       X_train, y_train),
    ("Validation",  X_val,   y_val),
    ("Test",        X_test,  y_test),
]:
    n_norm = (y_s == 0).sum()
    n_anom = (y_s == 1).sum()
    pct    = n_anom / len(y_s) * 100
    print(f"    {name:<12} {len(y_s):>10,} {n_norm:>10,} {n_anom:>10,} {pct:>11.2f}%")

# Vérification : total des splits = dataset complet
assert len(y_train) + len(y_val) + len(y_test) == len(y), "Erreur dans les splits !"
print(f"\n    -> Total vérifié : {len(y_train)+len(y_val)+len(y_test):,} = {len(y):,} ✓")

# Sauvegarde des splits
np.save(f"{OUTPUT_DIR}/X_train.npy", X_train)
np.save(f"{OUTPUT_DIR}/X_val.npy",   X_val)
np.save(f"{OUTPUT_DIR}/X_test.npy",  X_test)
np.save(f"{OUTPUT_DIR}/y_train.npy", y_train)
np.save(f"{OUTPUT_DIR}/y_val.npy",   y_val)
np.save(f"{OUTPUT_DIR}/y_test.npy",  y_test)

print(f"\n    -> Datasets sauvegardés dans '{OUTPUT_DIR}/' :")
for fname in ['X_train','X_val','X_test','y_train','y_val','y_test']:
    path = f"{OUTPUT_DIR}/{fname}.npy"
    size = os.path.getsize(path) / 1024 / 1024
    print(f"       {fname}.npy  —  {size:.1f} MB")


# ═══════════════════════════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("  Pipeline de prétraitement terminé avec succès")
print(f"  Features        : {len(feature_cols)}")
print(f"  Train           : {X_train.shape}")
print(f"  Validation      : {X_val.shape}")
print(f"  Test            : {X_test.shape}")
print(f"  Artefacts dans  : {OUTPUT_DIR}/")
print("=" * 65)