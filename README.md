<div align="center">

# SynthGuard Intelligence

**Plateforme de Due Diligence IA pour cabinets de consulting B2B**

*"Analysez vos prospects B2B en quelques secondes. Avant que ça coûte cher."*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4.1-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Kafka](https://img.shields.io/badge/Apache_Kafka-Streaming-231F20?style=flat-square&logo=apachekafka&logoColor=white)](https://kafka.apache.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/Licence-Académique-00B09B?style=flat-square)](/)

**El Houti Tlemcani Yahya** · ENSA Fès · 3IACN
</div>

---

## 📋 Contexte

SynthGuard Intelligence est une plateforme complète de **Due Diligence IA** développée dans le cadre d'un stage PFA (Projet de Fin d'Année) à **ELAVI** (juin — août 2026).

**Problématique :** Dans le consulting B2B, les décisions critiques — signature de contrats, accords de crédit, audits de conformité — reposent sur des analyses manuelles lentes et coûteuses.

**Solution :** Un moteur Beta-VAE entraîné sur 505 000 profils d'entreprises synthétiques, capable de détecter 4 types d'anomalies financières et structurelles en temps réel via un pipeline Apache Kafka.

---

## ✨ Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| 🔍 **5 Modules métier** | Due Diligence, Compliance & AML, Credit Risk, Audit, Business Advisor |
| ⚡ **Temps réel** | Pipeline Kafka → Beta-VAE → MongoDB (< 500ms bout-en-bout) |
| 🧠 **Explication IA** | SHAP-like : décomposition de l'erreur de reconstruction par feature |
| 📊 **Dashboard analytique** | KPIs live, PieChart, BarChart, mise à jour toutes les 15s |
| 📈 **Page Analytics** | Timeline, par secteur, par module, Top 10 risques |
| 🤖 **Chatbot IA** | Claude Sonnet 5 (OpenRouter) avec contexte temps réel injecté |
| 🎮 **Mode démonstration** | 4 scénarios pré-remplis (normal, coquille vide, filiale fantôme, outlier) |
| 🔐 **Authentification** | JWT localStorage + gestion utilisateurs par invitation |
| 📄 **Export PDF** | Rapport professionnel par analyse (ReportLab) |
| 🔄 **Comparaison** | Deux entreprises côte à côte sur le même module |

---

## 🏗 Architecture

```
PostgreSQL (505K profils) → Apache Kafka → Consumer VAE → MongoDB → FastAPI → React
```

```
SynthGuard/
├── api/
│   └── app_api.py              # FastAPI — 5 modules + PDF + SHAP + Auth
├── core/
│   ├── vae.py                  # Beta-VAE (KL Annealing + Free Bits)
│   ├── gan.py                  # CTGAN — génération d'anomalies
│   ├── s6_vae_gan_link.py      # Connexion espace latent VAE-GAN
│   └── detector.py             # Score hybride + grid search
├── data/
│   ├── generate_synthguard.py  # Génération dataset + PostgreSQL
│   ├── preprocess_synthguard.py# Nettoyage, normalisation, splits
│   ├── producer_kafka.py       # Simulation flux masse (200 msg/s)
│   └── consumer_kafka.py       # Détection temps réel + 5 interpréteurs
├── frontend/
│   └── src/
│       ├── context/            # AuthContext (JWT localStorage)
│       ├── pages/              # 10 pages React
│       └── components/         # Navbar, ResultCard, ShapExplainer, Chatbot
├── artifacts/                  # scaler.pkl + feature_cols.pkl
├── models/                     # vae_best.pt + detector_config.pkl
└── docker-compose.yml          # Kafka + Zookeeper + MongoDB
```

---

## 🛠 Stack Technique

| Couche | Technologies |
|--------|-------------|
| **Deep Learning** | PyTorch 2.4.1, Beta-VAE, CTGAN (SDV 1.17) |
| **Données** | PostgreSQL 16, MongoDB, Pandas, NumPy, Scikit-learn |
| **Streaming** | Apache Kafka 7.5 (Confluent), kafka-python |
| **Backend** | FastAPI 0.115, Uvicorn, ReportLab 4.2.2 |
| **Frontend** | React 18.3, Vite 5.4, TailwindCSS 3.4, Recharts |
| **IA Conversationnelle** | Claude Sonnet 5 via OpenRouter API |
| **Auth** | JWT simulé + localStorage |
| **DevOps** | Docker, Docker Compose |

---

## 🧠 Moteur IA — Beta-VAE

### Principe
Le Beta-VAE apprend la **distribution statistique des entreprises normales**. À l'inférence, il reconstruit le profil soumis — une erreur élevée signale une anomalie.

```
Score(x) = MSE(x, VAE(x)) = (1/n) × Σ(xᵢ - x̂ᵢ)²
```

### Architecture PyTorch
```
Encodeur : 20 features → Linear(64)+BN+ReLU → Linear(32)+BN+ReLU → μ(8), σ(8)
Décodeur : z(8) → Linear(32)+BN+ReLU → Linear(64)+BN+ReLU → Linear(20)+Sigmoid
Paramètres : 8 036 | Meilleur epoch : 47/100 | Device : CPU
```

### Résolution du Posterior Collapse
| Problème | Solution | Impact |
|----------|----------|--------|
| KL → 0 dès epoch 10 | KL Annealing (warmup=30) | F1 : 0.15 → **0.95** |
| Encodeur ignoré | Free Bits (0.1 nats/dim) | Recall : 51% → **100%** |
| Beta trop élevé | Beta : 2.0 → **1.0** | FPR : 5% → **0.09%** |

---

## 📊 Résultats

<div align="center">

| Métrique | Valeur |
|----------|--------|
| **AUC-ROC** | **0.999998** |
| **F1-Score** | **0.9524** |
| **Precision** | **90.91%** |
| **Recall** | **100%** |
| **FPR** | **0.09%** |
| **Separation ratio** | **x86.6** |
| Seuil τ | 0.020519 |
| Score moyen (normaux) | 0.010303 |
| Score moyen (anomalies) | 0.892431 |

</div>

### Matrice de confusion (test set : 50 499 profils)

|  | Prédit Normal | Prédit Anomalie |
|--|:---:|:---:|
| **Réel Normal** | 49 955 ✅ | 44 ❌ |
| **Réel Anomalie** | **0** ✅ | 500 ✅ |

---

## 🔍 Types d'Anomalies Détectés

| Type | Description | Exemple |
|------|-------------|---------|
| **Coquille vide** | Créée ≥ 2025, 1-5 emp, revenue 15 000-50 000 M$ | Fraude, blanchiment |
| **Outlier sectoriel** | Revenue impossible pour le secteur (Entertainment > 80 000 M$) | Falsification |
| **Filiale fantôme** | Filiale déclarée, revenue < 0.10 M$, 1 employé | Évasion fiscale |
| **Saisie aberrante** | Revenue négatif, année future, employés < 0 | Injection/erreur CRM |

---

## 📦 Les 5 Modules Métier

### Due Diligence
Analyse prospect avant signature. Verdict : `APPROUVER` / `INVESTIGUER` / `SUSPENDRE` / `REJETER`

### Compliance & AML
Détection blanchiment et fraude fiscale. Score AML 0-100. Red flags : juridictions à risque, filiales inactives.

### Credit Risk
Solvabilité avant crédit. Calcule : `debt_ratio`, `repayment_capacity`, `credit_limit_est`.

### Audit Automatisé
Non-conformité avec codes `AUD-001` à `AUD-004`. Score audit = 100 - (findings × 20).

### Business Advisor
Viabilité entrepreneuriale — logique inversée. `viability_score = max(0, 100 - score × 500)`.

---

## 🚀 Installation

### Prérequis
- Docker & Docker Compose
- Python 3.12
- Node.js 20+

### Lancement

```bash
# 1. Cloner le repo
git clone https://github.com/Yahya-wa3er/SynthGuard.git
cd SynthGuard

# 2. Variables d'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# 3. Infrastructure Docker
docker-compose up -d

# 4. Environnement Python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Consumer Kafka
python data/consumer_kafka.py

# 6. API FastAPI
python -m uvicorn api.app_api:app --reload --port 8000

# 7. Frontend React
cd frontend
npm install
npm run dev
```

Accès : `http://localhost:3000`

### Compte admin par défaut
```
Email    : yahya@synthguard.ai
Mot de passe : SynthGuard2026!
```

### Variables d'environnement (.env)

```env
# Base de données
DATABASE_URL=postgresql://synthguard:synthguard_pass@localhost:5432/synthguard
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=synthguard_mongodb

# Kafka
KAFKA_BOOTSTRAP=localhost:9092
KAFKA_TOPIC=synthguard-transactions

# Modèles
MODELS_DIR=./models
ARTIFACTS_DIR=./artifacts

# Frontend
VITE_OPENROUTER_API_KEY=your_openrouter_key
VITE_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

---

## 🗄 Dataset

| Type | Volume | Proportion |
|------|--------|------------|
| Données normales | 500 000 | 99.01% |
| Anomalies (4 types) | 5 000 | 0.99% |
| **Total** | **505 000** | **100%** |

Données 100% synthétiques — aucune vraie donnée client (conformité légale, RGPD).

---

## 🔐 Authentification

- JWT simulé côté frontend (localStorage)
- Accès sur invitation — l'admin crée les comptes
- Page `/admin/users` pour gérer les utilisateurs
- Logout avec révocation du token

---

## 📄 Licence

Projet académique — PFA ENSA Fès 2026. Usage éducatif uniquement.

---

<div align="center">

**SynthGuard Intelligence v2.0**

El Houti Tlemcani Yahya · ENSA Fès 2026 · Génie Informatique · IA & Confiance Numérique

</div>
