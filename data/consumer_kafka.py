"""
SynthGuard Intelligence — data/kafka_consumer.py
==================================================
Consumer evenementiel pur — version 2.0
Gere les 5 modules metier + sauvegarde interpretation dans MongoDB.

Auteur  : El Houti Tlemcani Yahya
Projet  : SynthGuard Intelligence
"""

import json
import time
import signal
import sys
import os
import numpy as np
import torch
import torch.nn as nn
import joblib
from kafka          import KafkaConsumer
from kafka.errors   import KafkaConnectionError
from pymongo        import MongoClient
from datetime       import datetime, UTC
from dotenv         import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

KAFKA_BOOTSTRAP  = "localhost:9092"
TOPIC            = "synthguard-transactions"
CONSUMER_GROUP   = "synthguard-realtime"

MONGO_URI        = "mongodb://localhost:27017/"
MONGO_DB         = "synthguard_mongodb"
COLLECTION       = "realtime_logs"

ARTIFACTS        = "./artifacts"
MODELS_DIR       = "./models"
DEVICE           = torch.device("cuda" if torch.cuda.is_available() else "cpu")



# ── Features (meme ordre que S2) ─────────────────────────────────────────────
SECTOR_COLS   = ['sector_entertainment','sector_medical',
                 'sector_retail','sector_software','sector_technolgy']
LOCATION_COLS = ['office_location_Canada','office_location_France',
                 'office_location_Germany','office_location_United Kingdom',
                 'office_location_United States']

# ── Labels metier ─────────────────────────────────────────────────────────────
ANOMALY_TYPE_LABELS = {
    0: "Normal",
    1: "Société écran / Coquille vide",
    2: "Outlier sectoriel",
    3: "Filiale fantôme",
    4: "Saisie aberrante / Données invalides",
}

# ── Benchmarks sectoriels (meme que app_api) ──────────────────────────────────
SECTOR_BENCHMARKS = {
    "technolgy"    : {"min_revenue": 500,  "min_employees": 20,  "min_budget": 100_000},
    "medical"      : {"min_revenue": 800,  "min_employees": 30,  "min_budget": 200_000},
    "software"     : {"min_revenue": 300,  "min_employees": 10,  "min_budget": 80_000},
    "retail"       : {"min_revenue": 200,  "min_employees": 15,  "min_budget": 50_000},
    "entertainment": {"min_revenue": 150,  "min_employees": 10,  "min_budget": 40_000},
}

RISK_LEVELS = {
    "low"     : {"label": "Faible",   "color": "#10b981", "emoji": "🟢"},
    "moderate": {"label": "Modéré",   "color": "#f59e0b", "emoji": "🟡"},
    "high"    : {"label": "Élevé",    "color": "#f97316", "emoji": "🟠"},
    "critical": {"label": "Critique", "color": "#ef4444", "emoji": "🔴"},
}

TYPE_LABELS = {
    0: "Normal",
    1: "Société écran / Coquille vide",
    2: "Outlier sectoriel",
    3: "Filiale fantôme",
    4: "Saisie aberrante / Données invalides",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ARCHITECTURE VAE (identique S3)
# ═══════════════════════════════════════════════════════════════════════════════

class BetaVAE(nn.Module):
    def __init__(self, input_dim, latent_dim, hidden_dims):
        super().__init__()
        enc = []; d = input_dim
        for h in hidden_dims:
            enc += [nn.Linear(d,h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(0.1)]
            d = h
        self.encoder   = nn.Sequential(*enc)
        self.fc_mu     = nn.Linear(hidden_dims[-1], latent_dim)
        self.fc_logvar = nn.Linear(hidden_dims[-1], latent_dim)
        dec = []; d = latent_dim
        for h in reversed(hidden_dims):
            dec += [nn.Linear(d,h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(0.1)]
            d = h
        dec += [nn.Linear(hidden_dims[0], input_dim), nn.Sigmoid()]
        self.decoder = nn.Sequential(*dec)

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def forward(self, x):
        mu, _ = self.encode(x)
        x_hat = self.decoder(mu)
        return x_hat, mu


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CHARGEMENT DES MODELES (une seule fois au demarrage)
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("  SynthGuard Intelligence — Consumer v2.0")
print("=" * 60)
print(f"\n[INIT] Chargement des modeles sur {DEVICE}...")

scaler        = joblib.load(f"{ARTIFACTS}/scaler.pkl")
feature_cols  = joblib.load(f"{ARTIFACTS}/feature_cols.pkl")
detector_cfg  = joblib.load(f"{MODELS_DIR}/detector_config.pkl")

THRESHOLD     = detector_cfg["threshold"]
SEVERITY_LVLS = detector_cfg["severity_levels"]
VAE_CFG       = detector_cfg["vae_config"]

print(f"[INIT] Scaler        : {len(feature_cols)} features")
print(f"[INIT] Seuil         : {THRESHOLD:.6f}")
print(f"[INIT] Sévérités     : {SEVERITY_LVLS}")

vae = BetaVAE(
    input_dim   = VAE_CFG["input_dim"],
    latent_dim  = VAE_CFG["latent_dim"],
    hidden_dims = VAE_CFG["hidden_dims"],
).to(DEVICE)
vae.load_state_dict(torch.load(
    f"{MODELS_DIR}/vae_best.pt", map_location=DEVICE
))
vae.eval()
print(f"[INIT] VAE           : chargé et en mode eval")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FONCTIONS DE TRAITEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def preprocess(msg: dict) -> np.ndarray:
    """Transforme le message JSON en vecteur normalise."""
    year      = float(msg.get("year_established", 2000))
    revenue   = float(msg.get("revenue", 0.0))
    employees = float(msg.get("employees", 1))
    has_sub   = 1.0 if msg.get("subsidiary_of") else 0.0
    sector    = str(msg.get("sector", "")).lower().strip()
    location  = str(msg.get("office_location", "")).strip()

    sector_ohe   = {c: 0.0 for c in SECTOR_COLS}
    if f"sector_{sector}" in sector_ohe:
        sector_ohe[f"sector_{sector}"] = 1.0

    location_ohe = {c: 0.0 for c in LOCATION_COLS}
    if f"office_location_{location}" in location_ohe:
        location_ohe[f"office_location_{location}"] = 1.0

    row = {
        "year_established": year,
        "revenue"         : revenue,
        "employees"       : employees,
        "has_subsidiary"  : has_sub,
        **sector_ohe,
        **location_ohe,
    }

    x        = np.array([row.get(c, 0.0) for c in feature_cols],
                        dtype=np.float32).reshape(1, -1)
    x_scaled = scaler.transform(x).astype(np.float32)
    return x_scaled


def compute_score(x_scaled: np.ndarray) -> float:
    """Inference VAE ultra-rapide avec torch.no_grad()."""
    x_tensor = torch.FloatTensor(x_scaled).to(DEVICE)
    with torch.no_grad():
        x_hat, mu = vae(x_tensor)
        score     = torch.mean((x_tensor - x_hat) ** 2).item()
    return float(score)


def get_severity(score: float) -> str:
    if score >= SEVERITY_LVLS["critique"]: return "critique"
    if score >= SEVERITY_LVLS["moderee"] : return "moderee"
    if score >= SEVERITY_LVLS["suspecte"]: return "suspecte"
    return "normale"


def get_risk_level(score: float) -> str:
    ratio = score / max(THRESHOLD, 1e-8)
    if ratio < 0.5 : return "low"
    if ratio < 1.0 : return "moderate"
    if ratio < 2.0 : return "high"
    return "critical"


def predict_anomaly_type(msg: dict, score: float) -> int:
    """Prédit le type d'anomalie depuis les règles métier."""
    if score < THRESHOLD:
        return 0

    year      = int(msg.get("year_established", 2000))
    revenue   = float(msg.get("revenue", 0.0))
    employees = int(msg.get("employees", 1))
    has_sub   = bool(msg.get("subsidiary_of"))
    sector    = str(msg.get("sector", "")).lower()

    if revenue < 0 or employees < 0 or year > 2024: return 4
    if has_sub and revenue < 1.0               : return 3
    if sector in ["retail","entertainment"] and revenue > 50000: return 2
    if year >= 2020 and employees <= 10 and revenue > 10000: return 1
    return 1


# ═══════════════════════════════════════════════════════════════════════════════
# 4. INTERPRETEURS METIER (meme logique que app_api)
# ═══════════════════════════════════════════════════════════════════════════════

def interpret_due_diligence(msg, score, anom_type, risk):
    alerts = []; recs = []
    if anom_type == 1:
        alerts.append("Structure incohérente — revenus vs taille anormaux")
        recs.append("Demander les bilans comptables des 3 dernières années")
        recs.append("Vérifier l'existence légale via le registre du commerce")
    if anom_type == 2:
        alerts.append("Métriques financières atypiques pour ce secteur")
        recs.append("Comparer avec les benchmarks sectoriels officiels")
    if anom_type == 3:
        alerts.append("Filiale avec activité nulle rattachée à un groupe")
        recs.append("Vérifier la structure capitalistique du groupe parent")
    if anom_type == 4:
        alerts.append("Données financières invalides dans le dossier")
        recs.append("Rejeter le dossier et demander des données certifiées")
    if not alerts:
        alerts.append("Aucune anomalie structurelle détectée")
        recs.append("Procéder aux vérifications d'usage avant signature")
    verdicts = {
        "low"     : "✅ APPROUVER — Profil conforme aux standards du secteur",
        "moderate": "⚠️  INVESTIGUER — Des points nécessitent vérification",
        "high"    : "🟠 SUSPENDRE — Anomalies significatives détectées",
        "critical": "🔴 REJETER — Profil incompatible avec la due diligence",
    }
    return {"verdict": verdicts[risk], "alerts": alerts, "recommendations": recs}


def interpret_compliance(msg, score, anom_type, risk):
    alerts = []; recs = []; red_flags = []
    revenue  = float(msg.get("revenue", 0))
    year     = int(msg.get("year_established", 2000))
    location = str(msg.get("office_location", ""))
    has_sub  = bool(msg.get("subsidiary_of"))
    HIGH_RISK = ["Kenya", "Philippines", "Brazil"]
    if anom_type == 1:
        red_flags.append("Entreprise récente avec flux financiers anormaux")
        alerts.append("Schéma potentiel de blanchiment — Structure type coquille")
    if anom_type == 3:
        red_flags.append("Filiale inactive avec rattachement suspect")
        alerts.append("Risque de structuration financière suspecte")
    if location in HIGH_RISK:
        red_flags.append(f"Juridiction à risque élevé : {location}")
    if year >= 2022 and revenue > 10000:
        red_flags.append("Entreprise < 3 ans avec revenus > 10M$")
    if has_sub and revenue < 1:
        red_flags.append("Filiale déclarée avec activité économique nulle")
    if red_flags:
        recs.append("Déclarer une alerte TRACFIN / autorité compétente")
        recs.append("Bloquer les transactions en attente d'investigation")
    else:
        recs.append("Profil conforme — surveillance standard applicable")
    verdicts = {
        "low"     : "✅ CONFORME — Aucun indicateur de blanchiment détecté",
        "moderate": "⚠️  VIGILANCE RENFORCÉE — Monitoring recommandé",
        "high"    : "🟠 ALERTE AML — Signaux de fraude détectés",
        "critical": "🔴 DÉCLARATION OBLIGATOIRE — Profil incompatible AML",
    }
    return {"verdict": verdicts[risk], "alerts": alerts,
            "red_flags": red_flags, "recommendations": recs,
            "aml_score": min(len(red_flags)*25, 100)}


def interpret_credit_risk(msg, score, anom_type, risk):
    alerts = []; recs = []
    revenue  = float(msg.get("revenue", 0))
    employees = int(msg.get("employees", 1))
    sector   = str(msg.get("sector","")).lower()
    year     = int(msg.get("year_established", 2000))
    bench    = SECTOR_BENCHMARKS.get(sector, {"min_revenue": 500, "min_employees": 20})
    debt_ratio = min(score * 100, 100)
    rpe      = revenue / max(employees, 1)
    repayment = "Élevée" if rpe > 100 else "Moyenne" if rpe > 30 else "Faible"
    credit_limit = max(0, revenue * 0.1 * (1 - min(score, 1))) if revenue > 0 else 0
    if revenue < bench["min_revenue"] * 0.5:
        alerts.append(f"Revenue insuffisant pour le secteur {sector}")
    if 2025 - year < 2:
        alerts.append("Entreprise trop récente — historique insuffisant")
    if anom_type in [1, 3, 4]:
        alerts.append("Anomalies structurelles — crédit non recommandé")
    verdicts = {
        "low"     : "✅ CRÉDIT ACCORDÉ — Profil financier sain",
        "moderate": "⚠️  CRÉDIT CONDITIONNEL — Garanties requises",
        "high"    : "🟠 CRÉDIT LIMITÉ — Montant réduit, surveillance renforcée",
        "critical": "🔴 CRÉDIT REFUSÉ — Risque de défaut trop élevé",
    }
    return {"verdict": verdicts[risk], "alerts": alerts, "recommendations": recs,
            "debt_ratio": round(debt_ratio,2), "repayment_capacity": repayment,
            "credit_limit_est": round(credit_limit, 2)}


def interpret_audit(msg, score, anom_type, risk):
    findings = []; conformities = []
    revenue  = float(msg.get("revenue", 0))
    employees = int(msg.get("employees", 1))
    sector   = str(msg.get("sector","")).lower()
    year     = int(msg.get("year_established", 2000))
    bench    = SECTOR_BENCHMARKS.get(sector, {"min_revenue": 500, "min_employees": 20})
    if anom_type == 1:
        findings.append({"code":"AUD-001","level":"Critique",
                         "description":"Cohérence structurelle — revenus vs taille incohérents"})
    if anom_type == 2:
        findings.append({"code":"AUD-002","level":"Majeur",
                         "description":"Benchmark sectoriel — métriques hors normes"})
    if anom_type == 3:
        findings.append({"code":"AUD-003","level":"Critique",
                         "description":"Structure groupe — filiale sans activité réelle"})
    if anom_type == 4:
        findings.append({"code":"AUD-004","level":"Bloquant",
                         "description":"Intégrité données — valeurs financières invalides"})
    if revenue > bench["min_revenue"] * 0.5:
        conformities.append("Revenue dans les normes sectorielles acceptables")
    if employees >= bench["min_employees"] * 0.5:
        conformities.append("Effectif cohérent avec l'activité déclarée")
    if 2025 - year >= 3:
        conformities.append("Ancienneté suffisante — historique disponible")
    verdicts = {
        "low"     : "✅ CONFORME — Aucune non-conformité majeure",
        "moderate": "⚠️  CONFORME AVEC RÉSERVES — Points d'attention documentés",
        "high"    : "🟠 NON-CONFORME — Non-conformités majeures à corriger",
        "critical": "🔴 AUDIT BLOQUANT — Non-conformités critiques",
    }
    return {"verdict": verdicts[risk], "findings": findings,
            "conformities": conformities,
            "audit_score": max(0, 100 - len(findings)*20),
            "recommendations": [f["description"] for f in findings]}


def interpret_business_advisor(msg, score, anom_type, risk):
    warnings = []; recs = []
    sector   = str(msg.get("sector","")).lower()
    revenue  = float(msg.get("revenue", 0))
    employees = int(msg.get("employees", 1))
    year     = int(msg.get("year_established", 2025))
    bench    = SECTOR_BENCHMARKS.get(sector, {"min_revenue":500,
                                               "min_employees":20, "min_budget":100_000})
    recommended_sector = sector
    for s, b in SECTOR_BENCHMARKS.items():
        if revenue >= b["min_budget"] * 0.001 and s != sector:
            recommended_sector = s
            break
    if revenue < bench["min_budget"] * 0.001:
        warnings.append(f"Budget insuffisant pour le secteur {sector}")
        recs.append(f"Budget minimum recommandé : ${bench['min_budget']:,}")
    if employees < bench["min_employees"]:
        warnings.append(f"Équipe trop réduite pour {sector}")
        recs.append(f"Effectif recommandé : {bench['min_employees']} personnes minimum")
    if year > 2025:
        warnings.append("Date de création dans le futur — planification à revoir")
    if not warnings:
        recs.append("Votre projet présente une cohérence satisfaisante")
        recs.append("Procéder à une étude de marché détaillée")
    viability = max(0, 100 - score * 500)
    actions   = {"low":"Lancer","moderate":"Ajuster puis lancer",
                 "high":"Collaborer / Pivoter","critical":"Attendre / Abandonner"}
    verdicts  = {
        "low"     : "✅ VIABLE — Projet cohérent avec les entreprises saines",
        "moderate": "⚠️  RISQUÉ — Fragilités détectées — ajustements recommandés",
        "high"    : "🟠 FRAGILE — Profil similaire aux entreprises qui échouent",
        "critical": "🔴 NON VIABLE — Fortement déconseillé en l'état",
    }
    return {"verdict": verdicts[risk], "warnings": warnings,
            "recommendations": recs, "action": actions[risk],
            "recommended_sector": recommended_sector,
            "viability_score": round(viability, 1)}


MODULE_INTERPRETERS = {
    "due_diligence"   : interpret_due_diligence,
    "compliance"      : interpret_compliance,
    "credit_risk"     : interpret_credit_risk,
    "audit"           : interpret_audit,
    "business_advisor": interpret_business_advisor,
}

# Module par defaut si absent du message
DEFAULT_MODULE = "due_diligence"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CONNEXIONS
# ═══════════════════════════════════════════════════════════════════════════════

mongo_client = MongoClient(MONGO_URI)
collection   = mongo_client[MONGO_DB][COLLECTION]
collection.create_index("detected_at")
collection.create_index("is_anomaly")
collection.create_index("module")
collection.create_index([("account", 1), ("module", 1), ("detected_at", -1)])
print(f"[INIT] MongoDB       : {MONGO_DB}.{COLLECTION}")

try:
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers   = KAFKA_BOOTSTRAP,
        group_id            = CONSUMER_GROUP,
        auto_offset_reset   = "earliest",
        enable_auto_commit  = True,
        value_deserializer  = lambda v: json.loads(v.decode("utf-8")),
        max_poll_records    = 10,
    )
    print(f"[INIT] Kafka Consumer: topic={TOPIC}")
except KafkaConnectionError as e:
    print(f"[!] Kafka inaccessible : {e}")
    sys.exit(1)

# ── Arret propre ──────────────────────────────────────────────────────────────
running = True

def handle_signal(sig, frame):
    global running
    print("\n[Consumer] Arret propre...")
    running = False

signal.signal(signal.SIGINT,  handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. BOUCLE EVENEMENTIELLE PURE
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n[Consumer] En attente de messages sur '{TOPIC}'...\n")

total_processed = 0
total_anomalies = 0

try:
    while running:
        records = consumer.poll(timeout_ms=1000)

        for tp, messages in records.items():
            for message in messages:
                if not running:
                    break

                t0  = time.time()
                msg = message.value

                # Module du message (formulaire ou producer)
                module = msg.get("module", DEFAULT_MODULE)
                if module not in MODULE_INTERPRETERS:
                    module = DEFAULT_MODULE

                print(f"\n[KAFKA] Nouveau message recu !")
                print(f"        Compte  : {msg.get('account','?')}")
                print(f"        Module  : {module}")
                print(f"        Revenue : {msg.get('revenue', 0)}")

                try:
                    # ── Pretraitement ─────────────────────────────────────
                    print(f"        --> Pretraitement...")
                    x_scaled = preprocess(msg)

                    # ── Score VAE ─────────────────────────────────────────
                    print(f"        --> Calcul du score VAE...")
                    score     = compute_score(x_scaled)
                    severity  = get_severity(score)
                    risk      = get_risk_level(score)
                    is_anom   = score >= THRESHOLD
                    anom_type = predict_anomaly_type(msg, score)
                    anom_lbl  = ANOMALY_TYPE_LABELS.get(anom_type, "Inconnu")

                    # ── Interpretation metier ─────────────────────────────
                    print(f"        --> Interpretation module={module}...")
                    interpret_fn   = MODULE_INTERPRETERS[module]
                    interpretation = interpret_fn(msg, score, anom_type, risk)

                    latency_ms = (time.time() - t0) * 1000

                    print(f"        Score    : {score:.6f}")
                    print(f"        Severite : {severity.upper()}")
                    print(f"        Risque   : {risk.upper()}")
                    print(f"        Anomalie : {'OUI — ' + anom_lbl if is_anom else 'NON'}")
                    print(f"        Verdict  : {interpretation.get('verdict','—')}")
                    print(f"        Latence  : {latency_ms:.2f}ms")

                    # ── Sauvegarde MongoDB ────────────────────────────────
                    doc = {
                        # Donnees brutes
                        "account"         : msg.get("account"),
                        "sector"          : msg.get("sector"),
                        "year_established": msg.get("year_established"),
                        "revenue"         : msg.get("revenue"),
                        "employees"       : msg.get("employees"),
                        "office_location" : msg.get("office_location"),
                        "subsidiary_of"   : msg.get("subsidiary_of"),
                        "source"          : msg.get("source", "kafka"),
                        # Resultat detection
                        "score"           : round(score, 6),
                        "threshold"       : THRESHOLD,
                        "is_anomaly"      : bool(is_anom),
                        "severity"        : severity,
                        "risk_level"      : risk,
                        "predicted_type"  : anom_type,
                        "anomaly_label"   : anom_lbl,
                        # Module et interpretation
                        "module"          : module,
                        "interpretation"  : interpretation,
                        # Metadonnees
                        "latency_ms"      : round(latency_ms, 2),
                        "detected_at"     : datetime.now(UTC),
                        "kafka_offset"    : message.offset,
                        "kafka_partition" : message.partition,
                    }

                    collection.insert_one(doc)
                    total_processed += 1
                    if is_anom:
                        total_anomalies += 1

                    if is_anom:
                        print(f"[MONGO] ALERTE sauvegardee ! {anom_lbl} — {severity.upper()}")
                    else:
                        print(f"[MONGO] Transaction normale sauvegardee.")

                except Exception as e:
                    print(f"[!] Erreur traitement : {e}")
                    import traceback
                    traceback.print_exc()

except KeyboardInterrupt:
    pass

finally:
    consumer.close()
    mongo_client.close()
    print(f"\n[Consumer] Arret — {total_processed} messages traites, "
          f"{total_anomalies} anomalies detectees")