"""
SynthGuard — core/vae.py
=========================
Implémentation du Beta-VAE pour l'apprentissage de la normalité.
Architecture : MLP Encodeur — espace latent gaussien — MLP Décodeur

Auteur  : El Houti Tlemcani Yahya
Projet  : SynthGuard — Détection d'anomalies B2B
Semaine : S3

Modifications S3-rev :
  - BETA             : 2.0  →  1.0
  - KL Annealing     : warmup linéaire 0→1 sur 30 epochs
  - Free Bits        : λ = 0.1 nats par dimension (évite posterior collapse)
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import joblib
import os
import time
import json

# ═══════════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

RANDOM_SEED  = 42
ARTIFACTS    = "../artifacts"
MODELS_DIR   = "../models"
os.makedirs(MODELS_DIR, exist_ok=True)

torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Hyperparamètres
INPUT_DIM     = 14        # nombre de features après encodage (issu de S2)
LATENT_DIM    = 8         # dimension de l'espace latent
HIDDEN_DIMS   = [64, 32]  # couches cachées encodeur et décodeur

# ── Modifications recommandées ───────────────────────────────────────────────
BETA          = 1.0       # ← Modif 1 : beta réduit à 1.0 (VAE standard)
KL_WARMUP     = 30        # ← Modif 2 : KL Annealing — warmup linéaire sur 30 epochs
FREE_BITS     = 0.1       # ← Modif 3 : Free Bits — seuil λ = 0.1 nats par dimension
# ─────────────────────────────────────────────────────────────────────────────

LEARNING_RATE = 1e-3
BATCH_SIZE    = 512
EPOCHS        = 100
DEVICE        = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 65)
print("  SynthGuard — Entraînement du Beta-VAE (rev. KL Annealing)")
print("=" * 65)
print(f"  Device      : {DEVICE}")
print(f"  Input dim   : {INPUT_DIM}")
print(f"  Latent dim  : {LATENT_DIM}")
print(f"  Beta        : {BETA}  (réduit de 2.0 → 1.0)")
print(f"  KL Warmup   : {KL_WARMUP} epochs  (annealing linéaire 0 → beta)")
print(f"  Free Bits   : {FREE_BITS} nats/dim  (évite posterior collapse)")
print(f"  Epochs      : {EPOCHS}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ARCHITECTURE DU BETA-VAE
# ═══════════════════════════════════════════════════════════════════════════════

class BetaVAE(nn.Module):
    """
    Beta-Variational Autoencoder pour données tabulaires.

    L'encodeur produit mu et log_var — paramètres de la distribution
    gaussienne dans l'espace latent.
    Le décodeur reconstruit les données depuis un échantillon z.

    Avec beta = 1 + KL Annealing + Free Bits :
      - L'annealing évite que le KL écrase la reconstruction en début d'entraînement.
      - Les Free Bits empêchent le posterior collapse sur les dimensions peu utilisées.
    """

    def __init__(self, input_dim, latent_dim, hidden_dims, beta=1.0):
        super(BetaVAE, self).__init__()

        self.input_dim  = input_dim
        self.latent_dim = latent_dim
        self.beta       = beta

        # ── Encodeur ────────────────────────────────────────────────────────
        encoder_layers = []
        in_dim = input_dim
        for h_dim in hidden_dims:
            encoder_layers.extend([
                nn.Linear(in_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(),
                nn.Dropout(0.1),
            ])
            in_dim = h_dim

        self.encoder = nn.Sequential(*encoder_layers)

        # Têtes séparées pour mu et log_var
        self.fc_mu     = nn.Linear(hidden_dims[-1], latent_dim)
        self.fc_logvar = nn.Linear(hidden_dims[-1], latent_dim)

        # ── Décodeur ────────────────────────────────────────────────────────
        decoder_layers = []
        in_dim = latent_dim
        for h_dim in reversed(hidden_dims):
            decoder_layers.extend([
                nn.Linear(in_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(),
                nn.Dropout(0.1),
            ])
            in_dim = h_dim

        decoder_layers.append(nn.Linear(hidden_dims[0], input_dim))
        decoder_layers.append(nn.Sigmoid())

        self.decoder = nn.Sequential(*decoder_layers)

        self._init_weights()

    def _init_weights(self):
        """Initialisation Xavier pour éviter la disparition du gradient."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)

    def reparameterize(self, mu, log_var):
        """
        Reparameterization trick :
        z = mu + sigma * epsilon,  epsilon ~ N(0, I)
        En mode évaluation, retourne directement mu (déterministe).
        """
        if self.training:
            std = torch.exp(0.5 * log_var)
            eps = torch.randn_like(std)
            return mu + eps * std
        else:
            return mu

    def encode(self, x):
        h       = self.encoder(x)
        mu      = self.fc_mu(h)
        log_var = self.fc_logvar(h)
        return mu, log_var

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, log_var = self.encode(x)
        z           = self.reparameterize(mu, log_var)
        x_hat       = self.decode(z)
        return x_hat, mu, log_var, z


# ═══════════════════════════════════════════════════════════════════════════════
# 2. HELPERS : KL ANNEALING + FREE BITS
# ═══════════════════════════════════════════════════════════════════════════════

def kl_annealing_weight(epoch: int, warmup: int, beta_target: float) -> float:
    """
    ── Modif 2 : KL Annealing ──────────────────────────────────────────────
    Retourne le poids effectif du terme KL à l'epoch courante.

    Durant les `warmup` premières epochs, le poids monte linéairement de 0
    jusqu'à beta_target.  Après le warmup, il reste constant à beta_target.

    Cela évite que le KL "écrase" la reconstruction au tout début et force
    le modèle à d'abord apprendre à bien reconstruire avant de régulariser.

    Exemple avec warmup=30, beta=1.0 :
        epoch 1  → weight = 0.033
        epoch 15 → weight = 0.500
        epoch 30 → weight = 1.000
        epoch 31 → weight = 1.000  (stable)
    """
    if warmup <= 0:
        return beta_target
    return beta_target * min(1.0, epoch / warmup)


def free_bits_kl(log_var: torch.Tensor, mu: torch.Tensor, free_bits: float) -> torch.Tensor:
    """
    ── Modif 3 : Free Bits ─────────────────────────────────────────────────
    Calcule la divergence KL par dimension en ignorant toute dimension dont
    la KL est inférieure au seuil `free_bits` (en nats).

    Formule analytique KL par dimension :
        kl_d = -0.5 * (1 + log_var_d - mu_d^2 - exp(log_var_d))

    On applique ensuite : kl_d_effective = max(kl_d, free_bits)

    Cela empêche le "posterior collapse" : le réseau ne peut plus ignorer une
    dimension latente en la forçant à coller exactement au prior N(0,1) (ce
    qui donnerait kl_d → 0 et laisserait cette dimension inutilisée).

    Retourne la KL totale (somme sur les dimensions, moyenne sur le batch).
    """
    # KL par dimension : shape (batch, latent_dim)
    kl_per_dim = -0.5 * (1.0 + log_var - mu.pow(2) - log_var.exp())

    # Appliquer le seuil free_bits dimension par dimension
    # mean sur le batch d'abord, puis max avec free_bits
    kl_mean_per_dim = kl_per_dim.mean(dim=0)                        # (latent_dim,)
    kl_clamped      = torch.clamp(kl_mean_per_dim, min=free_bits)   # (latent_dim,)

    # Somme sur les dimensions latentes → scalaire
    return kl_clamped.sum()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FONCTION DE PERTE ELBO (modifiée)
# ═══════════════════════════════════════════════════════════════════════════════

def vae_loss(x, x_hat, mu, log_var, beta_eff, free_bits=0.0):
    """
    Loss ELBO du VAE avec KL Annealing et Free Bits :

        L = Reconstruction + beta_eff * KL_free_bits

    beta_eff   : poids KL effectif au moment de l'appel (issu du scheduler d'annealing)
    free_bits  : seuil λ par dimension (0 = comportement classique)
    """

    # Reconstruction : MSE cumulé sur le batch
    recon_loss = nn.functional.mse_loss(x_hat, x, reduction='sum') / x.size(0)

    # KL avec Free Bits (Modif 3)
    if free_bits > 0.0:
        kl_loss = free_bits_kl(log_var, mu, free_bits)
    else:
        # Formule classique sans free bits
        kl_loss = (-0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())) / x.size(0)

    # Loss totale avec beta effectif (KL Annealing — Modif 2)
    total = recon_loss + beta_eff * kl_loss

    return total, recon_loss, kl_loss


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CHARGEMENT DES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[1/4] Chargement des données...")

X_train = np.load(f"{ARTIFACTS}/X_train.npy").astype(np.float32)
X_val   = np.load(f"{ARTIFACTS}/X_val.npy").astype(np.float32)
y_train = np.load(f"{ARTIFACTS}/y_train.npy")
y_val   = np.load(f"{ARTIFACTS}/y_val.npy")

# IMPORTANT : le VAE s'entraîne UNIQUEMENT sur les données normales
X_train_normal = X_train[y_train == 0]
X_val_normal   = X_val[y_val == 0]

print(f"    -> Train (normaux seulement) : {X_train_normal.shape}")
print(f"    -> Val   (normaux seulement) : {X_val_normal.shape}")
print(f"    -> Features                  : {X_train_normal.shape[1]}")

INPUT_DIM = X_train_normal.shape[1]

train_dataset = TensorDataset(torch.FloatTensor(X_train_normal))
val_dataset   = TensorDataset(torch.FloatTensor(X_val_normal))

train_loader = DataLoader(
    train_dataset,
    batch_size  = BATCH_SIZE,
    shuffle     = True,
    num_workers = 0,
    pin_memory  = DEVICE.type == "cuda"
)

val_loader = DataLoader(
    val_dataset,
    batch_size  = BATCH_SIZE,
    shuffle     = False,
    num_workers = 0
)

print(f"    -> Batches train : {len(train_loader)}")
print(f"    -> Batches val   : {len(val_loader)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INITIALISATION DU MODÈLE
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n[2/4] Initialisation du modèle...")

model = BetaVAE(
    input_dim   = INPUT_DIM,
    latent_dim  = LATENT_DIM,
    hidden_dims = HIDDEN_DIMS,
    beta        = BETA
).to(DEVICE)

optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

scheduler = optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode     = 'min',
    factor   = 0.5,
    patience = 10,
)

n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"    -> Paramètres entraînables : {n_params:,}")
print(f"    -> Architecture :")
print(f"       Encodeur  : {INPUT_DIM} → {HIDDEN_DIMS[0]} → {HIDDEN_DIMS[1]} → (mu={LATENT_DIM}, logvar={LATENT_DIM})")
print(f"       Décodeur  : {LATENT_DIM} → {HIDDEN_DIMS[1]} → {HIDDEN_DIMS[0]} → {INPUT_DIM}")
print(f"    -> KL Annealing : 0 → {BETA} sur {KL_WARMUP} epochs")
print(f"    -> Free Bits    : λ = {FREE_BITS} nats/dim")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. BOUCLE D'ENTRAÎNEMENT
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n[3/4] Entraînement ({EPOCHS} epochs)...")

history = {
    "train_loss": [], "val_loss": [],
    "train_recon": [], "val_recon": [],
    "train_kl": [],   "val_kl": [],
    "beta_eff": [],   # ← suivi du poids KL effectif epoch par epoch
}

best_val_loss    = float('inf')
best_epoch       = 0
patience_counter = 0
EARLY_STOP_PAT   = 20

t_train = time.time()

for epoch in range(1, EPOCHS + 1):

    # ── Poids KL effectif (KL Annealing — Modif 2) ──────────────────────────
    beta_eff = kl_annealing_weight(epoch, KL_WARMUP, BETA)

    # ── Phase entraînement ──────────────────────────────────────────────────
    model.train()
    train_total = train_recon = train_kl = 0.0

    for (batch,) in train_loader:
        batch = batch.to(DEVICE)
        optimizer.zero_grad()

        x_hat, mu, log_var, z = model(batch)
        loss, recon, kl = vae_loss(batch, x_hat, mu, log_var, beta_eff, FREE_BITS)

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        train_total += loss.item()
        train_recon += recon.item()
        train_kl    += kl.item()

    n_batches_train  = len(train_loader)
    train_total /= n_batches_train
    train_recon /= n_batches_train
    train_kl    /= n_batches_train

    # ── Phase validation ────────────────────────────────────────────────────
    model.eval()
    val_total = val_recon = val_kl = 0.0

    with torch.no_grad():
        for (batch,) in val_loader:
            batch = batch.to(DEVICE)
            x_hat, mu, log_var, z = model(batch)
            loss, recon, kl = vae_loss(batch, x_hat, mu, log_var, beta_eff, FREE_BITS)
            val_total += loss.item()
            val_recon += recon.item()
            val_kl    += kl.item()

    n_batches_val = len(val_loader)
    val_total /= n_batches_val
    val_recon /= n_batches_val
    val_kl    /= n_batches_val

    # ── Scheduler LR ────────────────────────────────────────────────────────
    prev_lr = optimizer.param_groups[0]["lr"]
    scheduler.step(val_total)
    new_lr = optimizer.param_groups[0]["lr"]
    if new_lr < prev_lr:
        print(f"    LR réduit : {prev_lr:.2e} -> {new_lr:.2e} à l'epoch {epoch}")

    # ── Historique ──────────────────────────────────────────────────────────
    history["train_loss"].append(train_total)
    history["val_loss"].append(val_total)
    history["train_recon"].append(train_recon)
    history["val_recon"].append(val_recon)
    history["train_kl"].append(train_kl)
    history["val_kl"].append(val_kl)
    history["beta_eff"].append(beta_eff)

    # ── Early stopping + sauvegarde du meilleur modèle ──────────────────────
    if val_total < best_val_loss:
        best_val_loss    = val_total
        best_epoch       = epoch
        patience_counter = 0
        torch.save(model.state_dict(), f"{MODELS_DIR}/vae_best.pt")
    else:
        patience_counter += 1

    # ── Log toutes les 10 epochs ────────────────────────────────────────────
    if epoch % 10 == 0 or epoch == 1:
        elapsed = time.time() - t_train
        print(
            f"    Epoch {epoch:>3}/{EPOCHS} | β_eff={beta_eff:.3f} | "
            f"Train: {train_total:.4f} (recon={train_recon:.4f}, kl={train_kl:.4f}) | "
            f"Val: {val_total:.4f} | "
            f"Best: {best_val_loss:.4f} @ E{best_epoch} | "
            f"{elapsed:.0f}s"
        )

    if patience_counter >= EARLY_STOP_PAT:
        print(f"\n    Early stopping déclenché à l'epoch {epoch}")
        print(f"    Aucune amélioration depuis {EARLY_STOP_PAT} epochs")
        break

elapsed_total = time.time() - t_train
print(f"\n    Entraînement terminé en {elapsed_total:.1f}s")
print(f"    Meilleur modèle : epoch {best_epoch}, val_loss = {best_val_loss:.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ÉVALUATION DU SCORE D'ANOMALIE (BASELINE)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n[4/4] Calcul du score d'anomalie sur le jeu de test...")

model.load_state_dict(torch.load(f"{MODELS_DIR}/vae_best.pt", map_location=DEVICE))
model.eval()

X_test = np.load(f"{ARTIFACTS}/X_test.npy").astype(np.float32)
y_test = np.load(f"{ARTIFACTS}/y_test.npy")

def compute_reconstruction_scores(model, X, batch_size=512):
    """
    Calcule l'erreur de reconstruction pour chaque ligne.
    Score élevé → le VAE reconstruit mal → probablement anormal.
    """
    scores  = []
    dataset = TensorDataset(torch.FloatTensor(X))
    loader  = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    with torch.no_grad():
        for (batch,) in loader:
            batch = batch.to(DEVICE)
            x_hat, mu, log_var, z = model(batch)
            recon_error = torch.mean((batch - x_hat) ** 2, dim=1)
            scores.extend(recon_error.cpu().numpy())

    return np.array(scores)

scores = compute_reconstruction_scores(model, X_test)

scores_normal  = scores[y_test == 0]
scores_anomaly = scores[y_test == 1]

print(f"\n    Scores de reconstruction (test set) :")
print(f"    {'─'*50}")
print(f"    Normaux   — mean: {scores_normal.mean():.6f}  std: {scores_normal.std():.6f}  max: {scores_normal.max():.6f}")
print(f"    Anomalies — mean: {scores_anomaly.mean():.6f}  std: {scores_anomaly.std():.6f}  max: {scores_anomaly.max():.6f}")
print(f"\n    Séparation (ratio moyen anomalie/normal) : x{scores_anomaly.mean()/scores_normal.mean():.1f}")

threshold = np.percentile(scores_normal, 99.9)
print(f"\n    Seuil adaptatif (percentile 95 normaux) : {threshold:.6f}")

y_pred = (scores > threshold).astype(int)

tp = ((y_pred == 1) & (y_test == 1)).sum()
fp = ((y_pred == 1) & (y_test == 0)).sum()
fn = ((y_pred == 0) & (y_test == 1)).sum()
tn = ((y_pred == 0) & (y_test == 0)).sum()

precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0

print(f"\n    Métriques baseline (VAE seul) :")
print(f"    {'─'*50}")
print(f"    Precision  : {precision:.4f}")
print(f"    Recall     : {recall:.4f}")
print(f"    F1-Score   : {f1:.4f}")
print(f"    Faux positifs (FPR) : {fpr:.4f}")

metrics = {
    "best_epoch"        : best_epoch,
    "best_val_loss"     : float(best_val_loss),
    "threshold_p95"     : float(threshold),
    "precision"         : float(precision),
    "recall"            : float(recall),
    "f1_score"          : float(f1),
    "fpr"               : float(fpr),
    "score_normal_mean" : float(scores_normal.mean()),
    "score_anomaly_mean": float(scores_anomaly.mean()),
    "separation_ratio"  : float(scores_anomaly.mean() / scores_normal.mean()),
    # ── Nouvelles clés liées aux modifications ─────────────────────────────
    "beta"              : BETA,
    "kl_warmup_epochs"  : KL_WARMUP,
    "free_bits_lambda"  : FREE_BITS,
}

with open(f"{MODELS_DIR}/vae_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

np.save(f"{ARTIFACTS}/vae_scores_test.npy", scores)
joblib.dump(
    {
        "threshold" : threshold,
        "beta"      : BETA,
        "latent_dim": LATENT_DIM,
        "kl_warmup" : KL_WARMUP,
        "free_bits" : FREE_BITS,
    },
    f"{MODELS_DIR}/vae_config.pkl"
)

with open(f"{MODELS_DIR}/vae_history.json", "w") as f:
    json.dump(history, f, indent=2)

print(f"\n    Artefacts sauvegardés :")
for fname in ["vae_best.pt", "vae_metrics.json", "vae_config.pkl", "vae_history.json"]:
    print(f"    -> {MODELS_DIR}/{fname}")
print(f"    -> {ARTIFACTS}/vae_scores_test.npy")

print("\n" + "=" * 65)
print("  VAE — Entraînement et évaluation terminés")
print(f"  F1-Score baseline : {f1:.4f}")
print(f"  Separation ratio  : x{scores_anomaly.mean()/scores_normal.mean():.1f}")
print("=" * 65)