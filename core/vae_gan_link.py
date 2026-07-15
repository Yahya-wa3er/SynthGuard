"""
SynthGuard — core/s6_vae_gan_link.py
======================================
Connexion VAE → GAN : encodage dans l'espace latent,
analyse de la frontière normale/anormale, génération
de nouvelles anomalies via perturbation latente.

Auteur  : El Houti Tlemcani Yahya
Projet  : SynthGuard — Détection d'anomalies B2B
Semaine : S6
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import joblib
import os
import json
import time

# ═══════════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

RANDOM_SEED  = 42
ARTIFACTS    = "../artifacts"
MODELS_DIR   = "../models"
os.makedirs(MODELS_DIR, exist_ok=True)

DEVICE       = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Paramètres de génération latente
N_LATENT_SAMPLES  = 3_000   # nouvelles anomalies générées via espace latent
PERTURBATION_STD  = 0.5     # écart-type de la perturbation gaussienne
                             # autour du mu des anomalies connues

torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

print("=" * 65)
print("  SynthGuard — S6 : Connexion VAE → GAN")
print("=" * 65)
print(f"  Device              : {DEVICE}")
print(f"  Anomalies latentes  : {N_LATENT_SAMPLES:,}")
print(f"  Perturbation std    : {PERTURBATION_STD}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. RECONSTRUCTION DU MODÈLE VAE
# ═══════════════════════════════════════════════════════════════════════════════

# Charger la configuration sauvegardée en S3
vae_config  = joblib.load(f"{MODELS_DIR}/vae_config.pkl")
LATENT_DIM  = vae_config["latent_dim"]
feature_cols = joblib.load(f"{ARTIFACTS}/feature_cols.pkl")
INPUT_DIM   = len(feature_cols)
HIDDEN_DIMS = [64, 32]

print(f"\n[0/4] Chargement du VAE...")
print(f"    -> Input dim  : {INPUT_DIM}")
print(f"    -> Latent dim : {LATENT_DIM}")


class BetaVAE(nn.Module):
    """Même architecture que S3 — doit être identique pour charger les poids."""

    def __init__(self, input_dim, latent_dim, hidden_dims):
        super().__init__()
        enc = []
        d = input_dim
        for h in hidden_dims:
            enc += [nn.Linear(d, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(0.1)]
            d = h
        self.encoder   = nn.Sequential(*enc)
        self.fc_mu     = nn.Linear(hidden_dims[-1], latent_dim)
        self.fc_logvar = nn.Linear(hidden_dims[-1], latent_dim)
        dec = []
        d = latent_dim
        for h in reversed(hidden_dims):
            dec += [nn.Linear(d, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(0.1)]
            d = h
        dec += [nn.Linear(hidden_dims[0], input_dim), nn.Sigmoid()]
        self.decoder = nn.Sequential(*dec)

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, lv = self.encode(x)
        std     = torch.exp(0.5 * lv)
        z       = mu + std * torch.randn_like(std) if self.training else mu
        return self.decode(z), mu, lv, z


vae = BetaVAE(INPUT_DIM, LATENT_DIM, HIDDEN_DIMS).to(DEVICE)
vae.load_state_dict(torch.load(
    f"{MODELS_DIR}/vae_best.pt", map_location=DEVICE
))
vae.eval()
print(f"    -> Poids VAE chargés depuis {MODELS_DIR}/vae_best.pt")


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRE : encodage en batch
# ═══════════════════════════════════════════════════════════════════════════════

def encode_to_latent(model, X, batch_size=512):
    """
    Encode un array numpy X dans l'espace latent.
    Retourne (mu, logvar) — shape (N, latent_dim) chacun.
    En mode eval, z = mu (déterministe, pas de bruit).
    """
    mus, logvars = [], []
    dataset = torch.utils.data.TensorDataset(torch.FloatTensor(X))
    loader  = torch.utils.data.DataLoader(dataset, batch_size=batch_size)

    with torch.no_grad():
        for (batch,) in loader:
            batch = batch.to(DEVICE)
            mu, lv = model.encode(batch)
            mus.append(mu.cpu().numpy())
            logvars.append(lv.cpu().numpy())

    return np.vstack(mus), np.vstack(logvars)


def decode_from_latent(model, Z, batch_size=512):
    """
    Décode un array de vecteurs latents Z vers l'espace des features.
    Retourne X_reconstructed — shape (N, input_dim).
    """
    reconstructed = []
    dataset = torch.utils.data.TensorDataset(torch.FloatTensor(Z))
    loader  = torch.utils.data.DataLoader(dataset, batch_size=batch_size)

    with torch.no_grad():
        for (batch,) in loader:
            batch = batch.to(DEVICE)
            x_hat = model.decode(batch)
            reconstructed.append(x_hat.cpu().numpy())

    return np.vstack(reconstructed)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ENCODER TOUTES LES ANOMALIES DANS L'ESPACE LATENT
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[1/4] Encodage des anomalies dans l'espace latent...")
t0 = time.time()

# Charger les données
X_train      = np.load(f"{ARTIFACTS}/X_train.npy").astype(np.float32)
y_train      = np.load(f"{ARTIFACTS}/y_train.npy")
X_synthetic  = np.load(f"{ARTIFACTS}/X_synthetic.npy").astype(np.float32)

# Séparer normaux et anomalies réelles du train set
X_normal_train = X_train[y_train == 0]
X_anom_real    = X_train[y_train == 1]

print(f"    -> Normaux train     : {X_normal_train.shape[0]:,}")
print(f"    -> Anomalies réelles : {X_anom_real.shape[0]:,}")
print(f"    -> Anomalies CTGAN   : {X_synthetic.shape[0]:,}")

# Encoder dans l'espace latent
mu_normal,  lv_normal  = encode_to_latent(vae, X_normal_train)
mu_anom,    lv_anom    = encode_to_latent(vae, X_anom_real)
mu_synth,   lv_synth   = encode_to_latent(vae, X_synthetic)

print(f"\n    Espaces latents encodés en {time.time()-t0:.1f}s :")
print(f"    -> mu_normal  shape : {mu_normal.shape}")
print(f"    -> mu_anom    shape : {mu_anom.shape}")
print(f"    -> mu_synth   shape : {mu_synth.shape}")

# Sauvegarder les représentations latentes pour UMAP / analyses futures
np.save(f"{ARTIFACTS}/mu_normal_train.npy",  mu_normal)
np.save(f"{ARTIFACTS}/mu_anom_real.npy",     mu_anom)
np.save(f"{ARTIFACTS}/mu_synth_ctgan.npy",   mu_synth)
print(f"    -> Représentations latentes sauvegardées")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ANALYSER LA FRONTIÈRE NORMALE / ANORMALE
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[2/4] Analyse de la frontière normale / anormale...")

# Distance euclidienne moyenne entre normaux et anomalies dans l'espace latent
# On utilise un sous-échantillon pour la rapidité
n_sample = min(5000, len(mu_normal))
idx      = np.random.choice(len(mu_normal), n_sample, replace=False)
mu_norm_sample = mu_normal[idx]

# Centroïde des anomalies réelles dans l'espace latent
centroid_anom   = mu_anom.mean(axis=0)
centroid_normal = mu_norm_sample.mean(axis=0)

# Distance centroïde normal → centroïde anomalie
dist_centroids = np.linalg.norm(centroid_anom - centroid_normal)

# Distance moyenne intra-normaux
dist_intra_normal = np.mean([
    np.linalg.norm(mu_norm_sample[i] - centroid_normal)
    for i in range(min(1000, n_sample))
])

# Distance moyenne intra-anomalies
dist_intra_anom = np.mean([
    np.linalg.norm(mu_anom[i] - centroid_anom)
    for i in range(len(mu_anom))
])

# Separation score : ratio distance inter / distance intra
separation_score = dist_centroids / (dist_intra_normal + dist_intra_anom + 1e-8)

print(f"    Distance centroïdes (normal vs anomalie) : {dist_centroids:.4f}")
print(f"    Dispersion intra-normaux                 : {dist_intra_normal:.4f}")
print(f"    Dispersion intra-anomalies               : {dist_intra_anom:.4f}")
print(f"    Separation score latent                  : {separation_score:.4f}")

if separation_score > 1.0:
    print(f"    -> Espace latent bien séparé ✓ (score > 1.0)")
else:
    print(f"    -> Séparation faible — les anomalies se mélangent aux normaux")

# Norme moyenne de mu par groupe
print(f"\n    Norme moyenne de mu dans l'espace latent :")
print(f"    Normaux   : {np.linalg.norm(mu_normal,  axis=1).mean():.4f}")
print(f"    Anomalies : {np.linalg.norm(mu_anom,    axis=1).mean():.4f}")
print(f"    Synthéti. : {np.linalg.norm(mu_synth,   axis=1).mean():.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GÉNÉRER DE NOUVELLES ANOMALIES VIA L'ESPACE LATENT (Lien VAE → GAN)
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[3/4] Génération d'anomalies via perturbation latente...")

"""
Principe du lien VAE → GAN :

1. On prend les mu des anomalies réelles dans l'espace latent
2. On ajoute une perturbation gaussienne contrôlée autour de ces mu
   z_new = mu_anomalie + perturbation_std * epsilon,  epsilon ~ N(0,I)
3. On passe z_new dans le décodeur VAE → nouvelles anomalies réalistes

Ces anomalies sont ancrées dans la région anormale de l'espace latent
mais avec une variété accrue — elles couvrent des zones non explorées
par le CTGAN en S5.
"""

# Combiner mu des anomalies réelles et synthétiques comme base
mu_all_anom = np.vstack([mu_anom, mu_synth])
n_base      = len(mu_all_anom)

# Échantillonner N_LATENT_SAMPLES points de base (avec remplacement si besoin)
idx_base = np.random.choice(n_base, N_LATENT_SAMPLES, replace=True)
mu_base  = mu_all_anom[idx_base]

# Perturbation gaussienne dans l'espace latent
epsilon  = np.random.randn(*mu_base.shape).astype(np.float32)
Z_new    = (mu_base + PERTURBATION_STD * epsilon).astype(np.float32)

print(f"    -> {N_LATENT_SAMPLES:,} vecteurs latents perturbés générés")
print(f"    -> Norme moyenne Z_new : {np.linalg.norm(Z_new, axis=1).mean():.4f}")

# Décoder les vecteurs latents → espace des features
X_latent_anomalies = decode_from_latent(vae, Z_new)
y_latent_anomalies = np.ones(len(X_latent_anomalies), dtype=np.int8)

print(f"    -> Décodage terminé : {X_latent_anomalies.shape}")

# Vérification qualité : les anomalies latentes doivent avoir
# un score de reconstruction VAE plus élevé que les normaux
with torch.no_grad():
    X_lat_t  = torch.FloatTensor(X_latent_anomalies).to(DEVICE)
    xhat, mu_check, lv_check, _ = vae(X_lat_t)
    scores_latent = torch.mean((X_lat_t - xhat) ** 2, dim=1).cpu().numpy()

X_norm_sample   = X_normal_train[:2000]
with torch.no_grad():
    X_ns_t = torch.FloatTensor(X_norm_sample).to(DEVICE)
    xhat_n, _, _, _ = vae(X_ns_t)
    scores_normal_ref = torch.mean((X_ns_t - xhat_n) ** 2, dim=1).cpu().numpy()

print(f"\n    Validation scores de reconstruction :")
print(f"    Normaux (référence)    : mean={scores_normal_ref.mean():.6f}")
print(f"    Anomalies latentes     : mean={scores_latent.mean():.6f}")
print(f"    Ratio                  : x{scores_latent.mean()/scores_normal_ref.mean():.1f}")

if scores_latent.mean() > scores_normal_ref.mean() * 2:
    print(f"    -> Anomalies latentes bien distinctes des normaux ✓")
else:
    print(f"    -> [!] Anomalies latentes proches des normaux — augmenter PERTURBATION_STD")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ENRICHIR LE DATASET AUGMENTÉ FINAL
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[4/4] Enrichissement du dataset augmenté...")

# Charger le dataset augmenté de S5
X_augmented_s5 = np.load(f"{ARTIFACTS}/X_augmented.npy").astype(np.float32)
y_augmented_s5 = np.load(f"{ARTIFACTS}/y_augmented.npy")

# Ajouter les anomalies latentes
X_augmented_final = np.vstack([X_augmented_s5, X_latent_anomalies])
y_augmented_final = np.concatenate([y_augmented_s5, y_latent_anomalies])

# Shuffle final
idx_shuffle       = np.random.permutation(len(X_augmented_final))
X_augmented_final = X_augmented_final[idx_shuffle]
y_augmented_final = y_augmented_final[idx_shuffle]

print(f"\n    Dataset augmenté final (S6) :")
print(f"    {'─'*48}")
print(f"    Dataset S5 (base)           : {len(X_augmented_s5):>10,}")
print(f"    + Anomalies latentes VAE    : {len(X_latent_anomalies):>10,}")
print(f"    {'─'*48}")
print(f"    Total final                 : {len(X_augmented_final):>10,}")
print(f"    Normaux                     : {(y_augmented_final==0).sum():>10,}")
print(f"    Toutes anomalies            : {(y_augmented_final==1).sum():>10,}")
print(f"    % anomalies                 : {(y_augmented_final==1).sum()/len(y_augmented_final)*100:>9.2f}%")

# Sauvegarde du dataset final S6
np.save(f"{ARTIFACTS}/X_augmented_s6.npy", X_augmented_final)
np.save(f"{ARTIFACTS}/y_augmented_s6.npy", y_augmented_final)

# Sauvegarde des anomalies latentes seules (pour analyses)
np.save(f"{ARTIFACTS}/X_latent_anomalies.npy", X_latent_anomalies)
np.save(f"{ARTIFACTS}/Z_latent_new.npy",        Z_new)

# Rapport S6
report_s6 = {
    "n_latent_anomalies"    : int(len(X_latent_anomalies)),
    "perturbation_std"      : float(PERTURBATION_STD),
    "separation_score"      : float(separation_score),
    "dist_centroids"        : float(dist_centroids),
    "score_ratio_latent"    : float(scores_latent.mean() / scores_normal_ref.mean()),
    "dataset_s5_size"       : int(len(X_augmented_s5)),
    "dataset_s6_size"       : int(len(X_augmented_final)),
    "pct_anomalies_s6"      : float((y_augmented_final==1).sum() / len(y_augmented_final) * 100),
}

with open(f"{MODELS_DIR}/s6_report.json", "w") as f:
    json.dump(report_s6, f, indent=2)

print(f"\n    Artefacts sauvegardés :")
for fname in ["X_augmented_s6.npy", "y_augmented_s6.npy",
              "X_latent_anomalies.npy", "Z_latent_new.npy"]:
    path = f"{ARTIFACTS}/{fname}"
    size = os.path.getsize(path) / 1024 / 1024
    print(f"    -> {fname:<35} {size:.1f} MB")
print(f"    -> {MODELS_DIR}/s6_report.json")

print("\n" + "=" * 65)
print("  S6 — Connexion VAE → GAN terminée")
print(f"  Separation score latent  : {separation_score:.4f}")
print(f"  Anomalies latentes       : {len(X_latent_anomalies):,}")
print(f"  Dataset final S6         : {len(X_augmented_final):,} lignes")
print(f"  Prêt pour S7 — Score hybride")
print("=" * 65)