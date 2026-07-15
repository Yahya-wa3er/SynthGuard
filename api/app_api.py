"""
SynthGuard Intelligence — api/app_api.py
==========================================
Backend FastAPI complet — 5 modules métier
Due Diligence | Compliance | Credit Risk | Audit | Business Advisor
+ Comparaison + Benchmarks sectoriels

Auteur  : El Houti Tlemcani Yahya
Projet  : SynthGuard Intelligence
"""

import json
import time
import os
import io
from datetime        import datetime
from fastapi         import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from kafka           import KafkaProducer
from kafka.errors    import KafkaConnectionError
from pymongo         import MongoClient
from bson            import ObjectId
from dotenv          import load_dotenv

# PDF
from reportlab.lib.pagesizes  import A4
from reportlab.lib            import colors
from reportlab.lib.styles     import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units      import cm
from reportlab.platypus       import (SimpleDocTemplate, Paragraph, Spacer,
                                       Table, TableStyle, HRFlowable)

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

KAFKA_BOOTSTRAP  = os.getenv("KAFKA_BOOTSTRAP",  "localhost:9092")
TOPIC            = os.getenv("KAFKA_TOPIC",       "synthguard-transactions")
MONGO_URI        = os.getenv("MONGO_URI",         "mongodb://localhost:27017/")
MONGO_DB         = os.getenv("MONGO_DB",          "synthguard")

app = FastAPI(
    title       = "SynthGuard Intelligence",
    description = "Plateforme de Due Diligence IA pour cabinets de consulting B2B",
    version     = "2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Kafka Producer ────────────────────────────────────────────────────────────
try:
    producer = KafkaProducer(
        bootstrap_servers = KAFKA_BOOTSTRAP,
        value_serializer  = lambda v: json.dumps(v).encode("utf-8"),
        acks              = "all",
        retries           = 3,
    )
    print("[API] Kafka Producer connecte")
except Exception as e:
    print(f"[!] Kafka non disponible : {e}")
    producer = None

# ── MongoDB ───────────────────────────────────────────────────────────────────
mongo      = MongoClient(MONGO_URI)
db         = mongo[MONGO_DB]
logs       = db["realtime_logs"]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DEFINITIONS LOCALES — risque, severite, labels (NE JAMAIS importer du consumer)
# ═══════════════════════════════════════════════════════════════════════════════

RISK_LEVELS = {
    "low"      : {"label": "Faible",    "color": "#10b981", "emoji": "🟢"},
    "moderate" : {"label": "Modéré",    "color": "#f59e0b", "emoji": "🟡"},
    "high"     : {"label": "Élevé",     "color": "#f97316", "emoji": "🟠"},
    "critical" : {"label": "Critique",  "color": "#ef4444", "emoji": "🔴"},
}

TYPE_LABELS = {
    0: "Normal",
    1: "Société écran / Coquille vide",
    2: "Outlier sectoriel",
    3: "Filiale fantôme",
    4: "Saisie aberrante / Données invalides",
}

# Seuils de référence sectoriels (revenue en M$, employees)
SECTOR_BENCHMARKS = {
    "technolgy"    : {"min_revenue": 500,   "min_employees": 20,  "min_budget": 100_000},
    "medical"      : {"min_revenue": 800,   "min_employees": 30,  "min_budget": 200_000},
    "software"     : {"min_revenue": 300,   "min_employees": 10,  "min_budget": 80_000},
    "retail"       : {"min_revenue": 200,   "min_employees": 15,  "min_budget": 50_000},
    "entertainment": {"min_revenue": 150,   "min_employees": 10,  "min_budget": 40_000},
}


def get_risk_level(score: float, threshold: float) -> str:
    """Calcule le niveau de risque a partir du score et du seuil."""
    ratio = score / max(threshold, 1e-8)
    if ratio < 0.5  : return "low"
    if ratio < 1.0  : return "moderate"
    if ratio < 2.0  : return "high"
    return "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. INTERPRETEUR METIER — coeur de la logique des 5 modules
# ═══════════════════════════════════════════════════════════════════════════════

def interpret_due_diligence(data: dict, score: float, anom_type: int, risk: str) -> dict:
    """Analyse prospect avant signature de contrat."""
    alerts = []
    recommendations = []

    if anom_type == 1:
        alerts.append("Structure d'entreprise incohérente — revenus déclarés anormaux vs taille réelle")
        recommendations.append("Demander les bilans comptables des 3 dernières années")
        recommendations.append("Vérifier l'existence légale via le registre du commerce")
    if anom_type == 2:
        alerts.append("Métriques financières atypiques pour ce secteur d'activité")
        recommendations.append("Comparer avec les benchmarks sectoriels officiels")
        recommendations.append("Solliciter un audit indépendant")
    if anom_type == 3:
        alerts.append("Filiale rattachée à un groupe mais activité nulle détectée")
        recommendations.append("Vérifier la structure capitalistique du groupe parent")
        recommendations.append("Exiger une lettre de confort de la maison mère")
    if anom_type == 4:
        alerts.append("Données financières invalides ou incomplètes dans le dossier")
        recommendations.append("Rejeter le dossier et demander des données certifiées")

    if not alerts:
        alerts.append("Aucune anomalie structurelle détectée")
        recommendations.append("Procéder aux vérifications d'usage avant signature")

    verdict_map = {
        "low"     : "✅ APPROUVER — Profil conforme aux standards du secteur",
        "moderate": "⚠️  INVESTIGUER — Des points nécessitent une vérification approfondie",
        "high"    : "🟠 SUSPENDRE — Anomalies significatives détectées avant toute décision",
        "critical": "🔴 REJETER — Profil incompatible avec les critères de due diligence",
    }

    return {
        "module"         : "Due Diligence",
        "verdict"        : verdict_map[risk],
        "alerts"         : alerts,
        "recommendations": recommendations,
        "risk_score"     : round(score, 6),
        "risk_level"     : RISK_LEVELS[risk],
        "anomaly_type"   : TYPE_LABELS[anom_type],
    }


def interpret_compliance(data: dict, score: float, anom_type: int, risk: str) -> dict:
    """Détection AML / blanchiment / fraude fiscale."""
    alerts = []
    recommendations = []
    red_flags = []

    revenue   = float(data.get("revenue", 0))
    employees = int(data.get("employees", 1))
    year      = int(data.get("year_established", 2000))
    location  = str(data.get("office_location", ""))
    has_sub   = bool(data.get("subsidiary_of"))

    HIGH_RISK_LOCATIONS = ["Kenya", "Philippines", "Brazil"]

    if anom_type == 1:
        red_flags.append("Entreprise récente avec flux financiers anormalement élevés")
        alerts.append("Schéma potentiel de blanchiment — Structure type 'coquille'")
    if anom_type == 3:
        red_flags.append("Filiale inactive avec rattachement à structure offshore")
        alerts.append("Risque de structuration financière suspecte")
    if location in HIGH_RISK_LOCATIONS:
        red_flags.append(f"Juridiction à risque élevé : {location}")
    if year >= 2022 and revenue > 10000:
        red_flags.append("Entreprise de moins de 3 ans avec revenus > 10M$")
    if has_sub and revenue < 1:
        red_flags.append("Filiale déclarée avec activité économique nulle")

    if red_flags:
        recommendations.append("Déclarer une alerte TRACFIN / autorité compétente")
        recommendations.append("Bloquer les transactions en attente d'investigation")
        recommendations.append("Demander les justificatifs d'origine des fonds")
    else:
        recommendations.append("Profil conforme — surveillance standard applicable")

    aml_score = min(len(red_flags) * 25, 100)

    verdict_map = {
        "low"     : "✅ CONFORME — Aucun indicateur de blanchiment détecté",
        "moderate": "⚠️  VIGILANCE RENFORCÉE — Monitoring transactionnel recommandé",
        "high"    : "🟠 ALERTE AML — Signaux de fraude fiscale ou blanchiment détectés",
        "critical": "🔴 DÉCLARATION OBLIGATOIRE — Profil incompatible avec les normes AML",
    }

    return {
        "module"         : "Compliance & AML",
        "verdict"        : verdict_map[risk],
        "red_flags"      : red_flags,
        "alerts"         : alerts,
        "recommendations": recommendations,
        "aml_score"      : aml_score,
        "risk_score"     : round(score, 6),
        "risk_level"     : RISK_LEVELS[risk],
        "anomaly_type"   : TYPE_LABELS[anom_type],
    }


def interpret_credit_risk(data: dict, score: float, anom_type: int, risk: str) -> dict:
    """Évaluation risque avant accord de crédit."""
    alerts = []
    recommendations = []

    revenue   = float(data.get("revenue", 0))
    employees = int(data.get("employees", 1))
    sector    = str(data.get("sector", "")).lower()
    year      = int(data.get("year_established", 2000))
    age       = 2025 - year

    bench     = SECTOR_BENCHMARKS.get(sector, {"min_revenue": 500, "min_employees": 20})
    debt_ratio = min(score * 100, 100)

    if revenue > 0 and employees > 0:
        revenue_per_employee = revenue / employees
        repayment_capacity   = "Élevée" if revenue_per_employee > 100 else \
                               "Moyenne" if revenue_per_employee > 30 else "Faible"
    else:
        repayment_capacity = "Indéterminée"

    if revenue < bench["min_revenue"] * 0.5:
        alerts.append(f"Revenue insuffisant pour le secteur {sector} — risque de défaut élevé")
    if age < 2:
        alerts.append("Entreprise trop récente — historique insuffisant pour scoring")
    if anom_type in [1, 3, 4]:
        alerts.append("Anomalies structurelles détectées — crédit non recommandé")

    credit_limit = max(0, revenue * 0.1 * (1 - min(score, 1))) if revenue > 0 else 0

    verdict_map = {
        "low"     : "✅ CRÉDIT ACCORDÉ — Profil financier sain",
        "moderate": "⚠️  CRÉDIT CONDITIONNEL — Garanties supplémentaires requises",
        "high"    : "🟠 CRÉDIT LIMITÉ — Montant maximum réduit, surveillance renforcée",
        "critical": "🔴 CRÉDIT REFUSÉ — Risque de défaut trop élevé",
    }

    return {
        "module"             : "Credit Risk",
        "verdict"            : verdict_map[risk],
        "alerts"             : alerts,
        "recommendations"    : recommendations,
        "debt_ratio"         : round(debt_ratio, 2),
        "repayment_capacity" : repayment_capacity,
        "credit_limit_est"   : round(credit_limit, 2),
        "risk_score"         : round(score, 6),
        "risk_level"         : RISK_LEVELS[risk],
        "anomaly_type"       : TYPE_LABELS[anom_type],
    }


def interpret_audit(data: dict, score: float, anom_type: int, risk: str) -> dict:
    """Rapport d'audit automatique."""
    findings    = []
    conformities = []

    revenue   = float(data.get("revenue", 0))
    employees = int(data.get("employees", 1))
    sector    = str(data.get("sector", "")).lower()
    year      = int(data.get("year_established", 2000))
    bench     = SECTOR_BENCHMARKS.get(sector, {"min_revenue": 500, "min_employees": 20})

    if anom_type == 1:
        findings.append({"code": "AUD-001", "level": "Critique",
                         "description": "Cohérence structurelle — revenus vs taille incohérents"})
    if anom_type == 2:
        findings.append({"code": "AUD-002", "level": "Majeur",
                         "description": "Benchmark sectoriel — métriques hors normes du secteur"})
    if anom_type == 3:
        findings.append({"code": "AUD-003", "level": "Critique",
                         "description": "Structure groupe — filiale sans activité économique réelle"})
    if anom_type == 4:
        findings.append({"code": "AUD-004", "level": "Bloquant",
                         "description": "Intégrité des données — valeurs financières invalides"})

    if revenue > bench["min_revenue"] * 0.5:
        conformities.append("Revenue dans les normes sectorielles acceptables")
    if employees >= bench["min_employees"] * 0.5:
        conformities.append("Effectif cohérent avec l'activité déclarée")
    if 2025 - year >= 3:
        conformities.append("Ancienneté suffisante — historique disponible")

    audit_score = 100 - len(findings) * 20

    verdict_map = {
        "low"     : "✅ CONFORME — Aucune non-conformité majeure détectée",
        "moderate": "⚠️  CONFORME AVEC RÉSERVES — Points d'attention documentés",
        "high"    : "🟠 NON-CONFORME — Non-conformités majeures à corriger",
        "critical": "🔴 AUDIT BLOQUANT — Non-conformités critiques — activité suspendue",
    }

    return {
        "module"        : "Audit Automatisé",
        "verdict"       : verdict_map[risk],
        "findings"      : findings,
        "conformities"  : conformities,
        "audit_score"   : max(0, audit_score),
        "n_findings"    : len(findings),
        "risk_score"    : round(score, 6),
        "risk_level"    : RISK_LEVELS[risk],
        "anomaly_type"  : TYPE_LABELS[anom_type],
        "recommendations": [f["description"] for f in findings],
    }


def interpret_business_advisor(data: dict, score: float, anom_type: int, risk: str) -> dict:
    """Conseil création d'entreprise — logique inversée."""
    recommendations = []
    warnings        = []

    sector    = str(data.get("sector", "")).lower()
    revenue   = float(data.get("revenue", 0))
    employees = int(data.get("employees", 1))
    year      = int(data.get("year_established", 2025))
    location  = str(data.get("office_location", ""))
    bench     = SECTOR_BENCHMARKS.get(sector, {"min_revenue": 500,
                                                "min_employees": 20,
                                                "min_budget": 100_000})

    recommended_sector = sector
    for s, b in SECTOR_BENCHMARKS.items():
        if revenue >= b["min_budget"] * 0.001 and s != sector:
            recommended_sector = s
            break

    if revenue < bench["min_budget"] * 0.001:
        warnings.append(f"Budget insuffisant pour le secteur {sector}")
        recommendations.append(
            f"Budget minimum recommandé : ${bench['min_budget']:,} "
            f"— envisager {recommended_sector} avec votre budget actuel"
        )
    if employees < bench["min_employees"]:
        warnings.append(f"Équipe trop réduite pour opérer dans {sector}")
        recommendations.append(
            f"Effectif recommandé : {bench['min_employees']} personnes minimum "
            f"— envisager des partenariats externes"
        )
    if year > 2025:
        warnings.append("Date de création dans le futur — planification à revoir")

    if not warnings:
        recommendations.append("Votre projet présente une cohérence satisfaisante")
        recommendations.append("Procéder à une étude de marché détaillée")
        recommendations.append("Consulter un expert-comptable pour la structuration")

    viability_score = max(0, 100 - score * 500)

    verdict_map = {
        "low"     : "✅ VIABLE — Votre projet est cohérent avec les entreprises saines du secteur",
        "moderate": "⚠️  RISQUÉ — Votre projet présente des fragilités — ajustements recommandés",
        "high"    : "🟠 FRAGILE — Ce profil ressemble aux entreprises qui échouent — revoir le plan",
        "critical": "🔴 NON VIABLE — Fortement déconseillé en l'état — pivot ou abandon recommandé",
    }

    action_map = {
        "low"     : "Lancer",
        "moderate": "Ajuster puis lancer",
        "high"    : "Collaborer / Pivoter",
        "critical": "Attendre / Abandonner",
    }

    return {
        "module"             : "Business Advisor",
        "verdict"            : verdict_map[risk],
        "action"             : action_map[risk],
        "warnings"           : warnings,
        "recommendations"    : recommendations,
        "recommended_sector" : recommended_sector,
        "viability_score"    : round(viability_score, 1),
        "risk_score"         : round(score, 6),
        "risk_level"         : RISK_LEVELS[risk],
        "anomaly_type"       : TYPE_LABELS[anom_type],
    }


MODULE_INTERPRETERS = {
    "due_diligence"   : interpret_due_diligence,
    "compliance"      : interpret_compliance,
    "credit_risk"     : interpret_credit_risk,
    "audit"           : interpret_audit,
    "business_advisor": interpret_business_advisor,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. HELPER — envoi Kafka + attente résultat MongoDB
# ═══════════════════════════════════════════════════════════════════════════════

def send_and_wait(data: dict, module: str, timeout: float = 5.0) -> dict:
    """
    Envoie le message dans Kafka et attend le résultat du consumer
    dans MongoDB (max timeout secondes).
    Retourne le document MongoDB ou None.
    """
    msg = {**data, "module": module, "source": "form", "timestamp": time.time()}

    if producer:
        producer.send(TOPIC, value=msg)
        producer.flush()
        print(f"[API] Message Kafka publie — module={module} compte={data.get('account','?')}")

    deadline = time.time() + timeout
    while time.time() < deadline:
        doc = logs.find_one(
            {"account": data.get("account"), "module": module, "source": "form"},
            sort=[("detected_at", -1)]
        )
        if doc:
            return doc
        time.sleep(0.1)

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ROUTES ANALYSE — 5 modules
# ═══════════════════════════════════════════════════════════════════════════════

async def analyze(request: Request, module: str):
    body = await request.json()

    required = ["account", "sector", "year_established", "revenue",
                "employees", "office_location"]
    for f in required:
        if f not in body:
            return JSONResponse({"error": f"Champ manquant : {f}"}, status_code=422)

    doc = send_and_wait(body, module)

    if doc:
        score     = doc.get("score", 0)
        anom_type = doc.get("predicted_type", 0)
        threshold = doc.get("threshold", 0.02)
        risk      = get_risk_level(score, threshold)
        interpret = MODULE_INTERPRETERS[module]
        result    = interpret(body, score, anom_type, risk)

        return JSONResponse({
            "status"   : "ok",
            "id"       : str(doc.get("_id", "")),
            "account"  : body.get("account"),
            "module"   : module,
            "timestamp": datetime.utcnow().isoformat(),
            "result"   : result,
        })

    return JSONResponse({
        "status" : "queued",
        "message": "Analyse en cours — résultat disponible dans l'historique",
    })


@app.post("/analyze/due-diligence")
async def route_due_diligence(request: Request):
    return await analyze(request, "due_diligence")

@app.post("/analyze/compliance")
async def route_compliance(request: Request):
    return await analyze(request, "compliance")

@app.post("/analyze/credit-risk")
async def route_credit_risk(request: Request):
    return await analyze(request, "credit_risk")

@app.post("/analyze/audit")
async def route_audit(request: Request):
    return await analyze(request, "audit")

@app.post("/analyze/business-advisor")
async def route_business_advisor(request: Request):
    return await analyze(request, "business_advisor")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ROUTE COMPARAISON — deux entreprises côte à côte
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/compare")
async def compare_companies(request: Request):
    """
    Compare deux profils d'entreprises en parallèle.
    Envoie les deux dans Kafka et attend les deux résultats.
    """
    body = await request.json()

    company_a = body.get("company_a")
    company_b = body.get("company_b")
    module    = body.get("module", "due_diligence")

    if not company_a or not company_b:
        return JSONResponse(
            {"error": "Les deux champs company_a et company_b sont requis"},
            status_code=422
        )

    required = ["account", "sector", "year_established",
                "revenue", "employees", "office_location"]
    for field in required:
        if field not in company_a:
            return JSONResponse({"error": f"company_a — champ manquant : {field}"}, status_code=422)
        if field not in company_b:
            return JSONResponse({"error": f"company_b — champ manquant : {field}"}, status_code=422)

    tag_a = f"compare_a_{int(time.time())}"
    tag_b = f"compare_b_{int(time.time())}"

    msg_a = {**company_a, "module": module, "source": tag_a, "timestamp": time.time()}
    msg_b = {**company_b, "module": module, "source": tag_b, "timestamp": time.time()}

    if producer:
        producer.send(TOPIC, value=msg_a)
        producer.send(TOPIC, value=msg_b)
        producer.flush()
        print(f"[API] Comparaison envoyée — {company_a['account']} vs {company_b['account']}")

    doc_a = doc_b = None
    deadline = time.time() + 6.0

    while time.time() < deadline:
        if not doc_a:
            doc_a = logs.find_one(
                {"account": company_a["account"], "source": tag_a},
                sort=[("detected_at", -1)]
            )
        if not doc_b:
            doc_b = logs.find_one(
                {"account": company_b["account"], "source": tag_b},
                sort=[("detected_at", -1)]
            )
        if doc_a and doc_b:
            break
        time.sleep(0.1)

    def format_result(doc, data):
        if not doc:
            return {"status": "pending", "account": data.get("account")}
        score     = doc.get("score", 0)
        threshold = doc.get("threshold", 0.02)
        risk      = get_risk_level(score, threshold)
        return {
            "account"       : doc.get("account"),
            "sector"        : doc.get("sector"),
            "score"         : round(score, 6),
            "risk_level"    : RISK_LEVELS.get(risk, {}),
            "severity"      : doc.get("severity"),
            "is_anomaly"    : doc.get("is_anomaly"),
            "anomaly_type"  : TYPE_LABELS.get(doc.get("predicted_type", 0), "—"),
            "interpretation": doc.get("interpretation", {}),
            "id"            : str(doc.get("_id", "")),
        }

    result_a = format_result(doc_a, company_a)
    result_b = format_result(doc_b, company_b)

    score_a = result_a.get("score", 1)
    score_b = result_b.get("score", 1)

    if score_a < score_b:
        recommendation = f"{company_a['account']} présente un profil plus sain"
        safer = "company_a"
    elif score_b < score_a:
        recommendation = f"{company_b['account']} présente un profil plus sain"
        safer = "company_b"
    else:
        recommendation = "Les deux entreprises présentent un niveau de risque similaire"
        safer = "equal"

    return JSONResponse({
        "status"        : "ok",
        "module"        : module,
        "company_a"     : result_a,
        "company_b"     : result_b,
        "recommendation": recommendation,
        "safer"         : safer,
        "timestamp"     : datetime.utcnow().isoformat(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ROUTE BENCHMARKS SECTORIELS
# ═══════════════════════════════════════════════════════════════════════════════

SECTOR_BENCHMARKS_FULL = {
    "technolgy": {
        "name"              : "Technology",
        "min_revenue"       : 500,
        "max_revenue"       : 500_000,
        "avg_revenue"       : 15_000,
        "min_employees"     : 20,
        "max_employees"     : 50_000,
        "avg_employees"     : 800,
        "min_budget"        : 100_000,
        "avg_age_years"     : 12,
        "typical_locations" : ["United States", "Germany", "United Kingdom"],
        "risk_profile"      : "Modéré",
        "growth_rate"       : "15-25% / an",
        "key_indicators"    : [
            "Revenue par employé > 50K$ = sain",
            "Croissance > 10%/an = normal",
            "R&D > 15% du CA = indicateur positif",
        ],
        "red_flags"         : [
            "Revenus > 10M$ avec < 10 employés",
            "Création < 1 an avec CA > 5M$",
            "Aucune présence digitale vérifiable",
        ],
    },
    "medical": {
        "name"              : "Medical & Healthcare",
        "min_revenue"       : 800,
        "max_revenue"       : 800_000,
        "avg_revenue"       : 25_000,
        "min_employees"     : 30,
        "max_employees"     : 100_000,
        "avg_employees"     : 1_500,
        "min_budget"        : 200_000,
        "avg_age_years"     : 18,
        "typical_locations" : ["United States", "Germany", "France"],
        "risk_profile"      : "Faible",
        "growth_rate"       : "8-12% / an",
        "key_indicators"    : [
            "Certifications réglementaires (FDA, CE) requises",
            "Effectif qualifié > 40% du total",
            "Investissement R&D > 20% du CA",
        ],
        "red_flags"         : [
            "Création récente sans certifications",
            "Revenus anormaux pour un petit effectif",
            "Absence de localisation dans un hub médical",
        ],
    },
    "software": {
        "name"              : "Software & SaaS",
        "min_revenue"       : 300,
        "max_revenue"       : 300_000,
        "avg_revenue"       : 8_000,
        "min_employees"     : 10,
        "max_employees"     : 20_000,
        "avg_employees"     : 250,
        "min_budget"        : 80_000,
        "avg_age_years"     : 8,
        "typical_locations" : ["United States", "United Kingdom", "Canada"],
        "risk_profile"      : "Modéré-Élevé",
        "growth_rate"       : "20-40% / an",
        "key_indicators"    : [
            "MRR (Monthly Recurring Revenue) stable",
            "Churn rate < 5%",
            "NPS > 40",
        ],
        "red_flags"         : [
            "Revenus très élevés sans produit identifiable",
            "Équipe < 5 avec CA > 5M$",
            "Pas de présence GitHub ou technique vérifiable",
        ],
    },
    "retail": {
        "name"              : "Retail & Distribution",
        "min_revenue"       : 200,
        "max_revenue"       : 50_000,
        "avg_revenue"       : 3_000,
        "min_employees"     : 15,
        "max_employees"     : 500_000,
        "avg_employees"     : 2_000,
        "min_budget"        : 50_000,
        "avg_age_years"     : 15,
        "typical_locations" : ["United States", "France", "Germany"],
        "risk_profile"      : "Modéré",
        "growth_rate"       : "3-8% / an",
        "key_indicators"    : [
            "Marge brute > 25%",
            "Rotation des stocks < 60 jours",
            "Présence physique ou e-commerce vérifiable",
        ],
        "red_flags"         : [
            "CA > 80M$ pour retail local avec < 100 employés",
            "Aucun point de vente ou plateforme identifiable",
            "Revenus 10x supérieurs à la moyenne sectorielle",
        ],
    },
    "entertainment": {
        "name"              : "Entertainment & Media",
        "min_revenue"       : 150,
        "max_revenue"       : 30_000,
        "avg_revenue"       : 2_000,
        "min_employees"     : 10,
        "max_employees"     : 50_000,
        "avg_employees"     : 500,
        "min_budget"        : 40_000,
        "avg_age_years"     : 10,
        "typical_locations" : ["United States", "United Kingdom", "France"],
        "risk_profile"      : "Élevé",
        "growth_rate"       : "5-15% / an",
        "key_indicators"    : [
            "Catalogue de contenus ou IP propriétaires",
            "Audience / abonnés vérifiables",
            "Partenariats avec distributeurs reconnus",
        ],
        "red_flags"         : [
            "Revenus > 50M$ sans catalogue identifiable",
            "Structure récente avec flux financiers massifs",
            "Aucune présence médiatique vérifiable",
        ],
    },
}


@app.get("/benchmarks")
async def get_all_benchmarks():
    """Retourne les benchmarks de tous les secteurs."""
    return {
        "sectors"   : list(SECTOR_BENCHMARKS_FULL.keys()),
        "benchmarks": SECTOR_BENCHMARKS_FULL,
        "updated_at": "2025-01",
        "source"    : "SynthGuard Intelligence — Base de référence sectorielle",
    }


@app.get("/benchmarks/{sector}")
async def get_sector_benchmark(sector: str):
    """Retourne les métriques de référence d'un secteur."""
    sector_key = sector.lower().strip()

    if sector_key not in SECTOR_BENCHMARKS_FULL:
        available = list(SECTOR_BENCHMARKS_FULL.keys())
        return JSONResponse(
            {"error": f"Secteur inconnu. Disponibles : {available}"},
            status_code=404
        )

    benchmark = dict(SECTOR_BENCHMARKS_FULL[sector_key])

    pipeline = [
        {"$match": {"sector": sector_key, "is_anomaly": False}},
        {"$group": {
            "_id"          : None,
            "avg_revenue"  : {"$avg": "$revenue"},
            "avg_employees": {"$avg": "$employees"},
            "count"        : {"$sum": 1},
        }}
    ]
    db_stats = list(logs.aggregate(pipeline))
    if db_stats and db_stats[0].get("count", 0) > 10:
        benchmark["db_avg_revenue"]   = round(db_stats[0].get("avg_revenue", 0), 2)
        benchmark["db_avg_employees"] = round(db_stats[0].get("avg_employees", 0), 1)
        benchmark["db_sample_size"]   = db_stats[0].get("count", 0)

    return {
        "sector"   : sector_key,
        "benchmark": benchmark,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ROUTES DASHBOARD & HISTORIQUE
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/dashboard/stats")
async def stats():
    """KPIs globaux pour le dashboard."""
    total     = logs.count_documents({})
    anomalies = logs.count_documents({"is_anomaly": True})

    pipeline_mod = [{"$group": {"_id": "$module", "count": {"$sum": 1},
                                "anomalies": {"$sum": {"$cond": ["$is_anomaly", 1, 0]}}}}]
    by_module = {r["_id"]: {"count": r["count"], "anomalies": r["anomalies"]}
                 for r in logs.aggregate(pipeline_mod) if r["_id"]}

    pipeline_sev = [{"$group": {"_id": "$severity", "count": {"$sum": 1}}}]
    by_severity  = {r["_id"]: r["count"] for r in logs.aggregate(pipeline_sev) if r["_id"]}

    avg_res   = list(logs.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$score"}}}]))
    avg_score = round(avg_res[0]["avg"], 5) if avg_res else 0.0

    critiques = list(
        logs.find({"severity": "critique"}, {"_id": 0, "account": 1,
                   "module": 1, "score": 1, "detected_at": 1})
            .sort("detected_at", -1).limit(5)
    )
    for c in critiques:
        if "detected_at" in c and hasattr(c["detected_at"], "isoformat"):
            c["detected_at"] = c["detected_at"].isoformat()

    return {
        "total"           : total,
        "anomalies"       : anomalies,
        "rate"            : round(anomalies / max(total, 1) * 100, 2),
        "avg_score"       : avg_score,
        "by_module"       : by_module,
        "by_severity"     : by_severity,
        "latest_critiques": critiques,
    }


@app.get("/dashboard/logs")
async def history(
    page        : int = 0,
    per_page    : int = 20,
    module      : str = "",
    severity    : str = "",
    is_anomaly  : str = "",
):
    """Historique paginé avec filtres."""
    query = {}
    if module    : query["module"]     = module
    if severity  : query["severity"]   = severity
    if is_anomaly: query["is_anomaly"] = is_anomaly.lower() == "true"

    total = logs.count_documents(query)
    docs  = list(
        logs.find(query, {"_id": 1, "account": 1, "sector": 1, "revenue": 1,
                           "employees": 1, "score": 1, "is_anomaly": 1,
                           "severity": 1, "module": 1, "predicted_type": 1,
                           "anomaly_label": 1, "detected_at": 1})
            .sort("detected_at", -1)
            .skip(page * per_page)
            .limit(per_page)
    )

    for d in docs:
        d["id"] = str(d.pop("_id"))
        if "detected_at" in d and hasattr(d["detected_at"], "isoformat"):
            d["detected_at"] = d["detected_at"].isoformat()

    return {"docs": docs, "total": total, "page": page, "per_page": per_page}


@app.get("/report/{doc_id}")
async def get_report(doc_id: str):
    """Récupère un rapport complet par ID."""
    try:
        doc = logs.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return JSONResponse({"error": "Rapport introuvable"}, status_code=404)
        doc["id"] = str(doc.pop("_id"))
        if "detected_at" in doc and hasattr(doc["detected_at"], "isoformat"):
            doc["detected_at"] = doc["detected_at"].isoformat()
        return doc
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. GÉNÉRATION PDF
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/report/{doc_id}/pdf")
async def generate_pdf(doc_id: str):
    """Génère un rapport PDF professionnel."""
    try:
        doc = logs.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return JSONResponse({"error": "Rapport introuvable"}, status_code=404)
    except Exception:
        return JSONResponse({"error": "ID invalide"}, status_code=400)

    buffer  = io.BytesIO()
    doc_pdf = SimpleDocTemplate(buffer, pagesize=A4,
                                 leftMargin=2*cm, rightMargin=2*cm,
                                 topMargin=2*cm,  bottomMargin=2*cm)
    styles  = getSampleStyleSheet()
    story   = []

    C_PRIMARY = colors.HexColor("#1e3a5f")
    C_ACCENT  = colors.HexColor("#2563eb")
    C_GRAY    = colors.HexColor("#64748b")
    C_LIGHT   = colors.HexColor("#f8fafc")
    C_RED     = colors.HexColor("#ef4444")
    C_GREEN   = colors.HexColor("#10b981")

    risk      = doc.get("severity", "normale")
    risk_color = {"normale": C_GREEN, "suspecte": colors.orange,
                  "moderee": colors.orangered, "critique": C_RED}.get(risk, C_GRAY)

    story.append(Paragraph(
        "<font color='#1e3a5f'><b>SynthGuard Intelligence</b></font>",
        ParagraphStyle("title", fontSize=22, spaceAfter=4)
    ))
    story.append(Paragraph(
        "Rapport d'Analyse IA — Due Diligence & Conformité B2B",
        ParagraphStyle("subtitle", fontSize=11, textColor=C_GRAY, spaceAfter=12)
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=C_ACCENT, spaceAfter=16))

    story.append(Paragraph("<b>Informations Générales</b>",
                            ParagraphStyle("h2", fontSize=13, textColor=C_PRIMARY, spaceAfter=8)))

    detected_at = doc.get("detected_at", datetime.utcnow())
    if hasattr(detected_at, "strftime"):
        date_str = detected_at.strftime("%d/%m/%Y à %H:%M:%S UTC")
    else:
        date_str = str(detected_at)

    module_labels = {
        "due_diligence"   : "Due Diligence",
        "compliance"      : "Compliance & AML",
        "credit_risk"     : "Credit Risk",
        "audit"           : "Audit Automatisé",
        "business_advisor": "Business Advisor",
    }

    info_data = [
        ["Compte analysé",   doc.get("account", "—")],
        ["Secteur",          doc.get("sector", "—")],
        ["Module d'analyse", module_labels.get(doc.get("module",""), doc.get("module","—"))],
        ["Date d'analyse",   date_str],
        ["Analysé par",      "SynthGuard Intelligence v2.0 — Moteur VAE"],
    ]
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (0,-1), C_LIGHT),
        ("TEXTCOLOR",   (0,0), (0,-1), C_PRIMARY),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, C_LIGHT]),
        ("PADDING",     (0,0), (-1,-1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("<b>Résultat de l'Analyse</b>",
                            ParagraphStyle("h2", fontSize=13, textColor=C_PRIMARY, spaceAfter=8)))

    score_data = [
        ["Score VAE",        f"{doc.get('score', 0):.6f}"],
        ["Niveau de risque", risk.upper()],
        ["Type d'anomalie",  TYPE_LABELS.get(doc.get("predicted_type", 0), "—")],
        ["Statut",           "ANOMALIE DÉTECTÉE" if doc.get("is_anomaly") else "NORMAL"],
    ]
    score_table = Table(score_data, colWidths=[5*cm, 12*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (0,-1), C_LIGHT),
        ("TEXTCOLOR",   (0,0), (0,-1), C_PRIMARY),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (1,1), (1,1), risk_color),
        ("FONTNAME",    (1,1), (1,1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (1,3), (1,3), C_RED if doc.get("is_anomaly") else C_GREEN),
        ("FONTNAME",    (1,3), (1,3), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, C_LIGHT]),
        ("PADDING",     (0,0), (-1,-1), 6),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("<b>Données Analysées</b>",
                            ParagraphStyle("h2", fontSize=13, textColor=C_PRIMARY, spaceAfter=8)))

    raw_data = [
        ["Année de création",  str(doc.get("year_established", "—"))],
        ["Revenue (M$)",       str(doc.get("revenue", "—"))],
        ["Employés",           str(doc.get("employees", "—"))],
        ["Localisation",       doc.get("office_location", "—")],
        ["Filiale de",         doc.get("subsidiary_of") or "Entité indépendante"],
    ]
    raw_table = Table(raw_data, colWidths=[5*cm, 12*cm])
    raw_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (0,-1), C_LIGHT),
        ("TEXTCOLOR",   (0,0), (0,-1), C_PRIMARY),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, C_LIGHT]),
        ("PADDING",     (0,0), (-1,-1), 6),
    ]))
    story.append(raw_table)
    story.append(Spacer(1, 16))

    interp   = doc.get("interpretation", {})
    recs     = interp.get("recommendations", [])
    alerts   = interp.get("alerts", interp.get("red_flags", interp.get("warnings", [])))
    verdict  = interp.get("verdict", "—")

    if verdict and verdict != "—":
        story.append(Paragraph("<b>Verdict</b>",
                                ParagraphStyle("h2", fontSize=13, textColor=C_PRIMARY, spaceAfter=6)))
        story.append(Paragraph(verdict,
                                ParagraphStyle("verdict", fontSize=11,
                                               textColor=risk_color, spaceAfter=12,
                                               fontName="Helvetica-Bold")))

    if alerts:
        story.append(Paragraph("<b>Alertes Détectées</b>",
                                ParagraphStyle("h2", fontSize=13, textColor=C_PRIMARY, spaceAfter=6)))
        for alert in alerts:
            story.append(Paragraph(
                f"• {alert}",
                ParagraphStyle("bullet", fontSize=9, textColor=C_RED,
                               leftIndent=12, spaceAfter=3)
            ))
        story.append(Spacer(1, 10))

    if recs:
        story.append(Paragraph("<b>Recommandations</b>",
                                ParagraphStyle("h2", fontSize=13, textColor=C_PRIMARY, spaceAfter=6)))
        for rec in recs:
            story.append(Paragraph(
                f"→ {rec}",
                ParagraphStyle("rec", fontSize=9, textColor=colors.HexColor("#1e3a5f"),
                               leftIndent=12, spaceAfter=3)
            ))
        story.append(Spacer(1, 16))

    story.append(HRFlowable(width="100%", thickness=0.5, color=C_GRAY, spaceAfter=8))
    story.append(Paragraph(
        "Ce rapport a été généré automatiquement par SynthGuard Intelligence. "
        "Il constitue une aide à la décision et ne remplace pas l'analyse d'un expert qualifié. "
        "SynthGuard Intelligence ne saurait être tenu responsable des décisions prises sur la "
        "base de ce rapport.",
        ParagraphStyle("disclaimer", fontSize=7, textColor=C_GRAY, spaceAfter=4)
    ))
    story.append(Paragraph(
        f"Généré le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M UTC')} — "
        "SynthGuard Intelligence v2.0",
        ParagraphStyle("footer", fontSize=7, textColor=C_GRAY)
    ))

    doc_pdf.build(story)
    buffer.seek(0)

    account_clean = str(doc.get("account", "rapport")).replace(" ", "_")[:30]
    filename      = f"SynthGuard_{account_clean}_{doc_id[:8]}.pdf"

    return Response(
        content      = buffer.read(),
        media_type   = "application/pdf",
        headers      = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ROUTES UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE SHAP — Explication par décomposition de l'erreur de reconstruction
# ═══════════════════════════════════════════════════════════════════════════════

import numpy as np
import torch
import torch.nn as nn
import joblib

# Chargement VAE et scaler (une seule fois au démarrage de l'API)
_vae_loaded   = False
_vae_model    = None
_vae_scaler   = None
_vae_features = None
_vae_cfg      = None

def _load_vae_once():
    global _vae_loaded, _vae_model, _vae_scaler, _vae_features, _vae_cfg
    if _vae_loaded:
        return

    ARTIFACTS  = os.getenv("ARTIFACTS_DIR",  "../artifacts")
    MODELS_DIR = os.getenv("MODELS_DIR",     "../models")

    try:
        _vae_scaler   = joblib.load(f"{ARTIFACTS}/scaler.pkl")
        _vae_features = joblib.load(f"{ARTIFACTS}/feature_cols.pkl")
        _vae_cfg      = joblib.load(f"{MODELS_DIR}/detector_config.pkl")

        vae_conf = _vae_cfg["vae_config"]

        class _BetaVAE(nn.Module):
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

            def forward(self, x):
                h      = self.encoder(x)
                mu     = self.fc_mu(h)
                x_hat  = self.decoder(mu)
                return x_hat, mu

        model = _BetaVAE(
            input_dim   = vae_conf["input_dim"],
            latent_dim  = vae_conf["latent_dim"],
            hidden_dims = vae_conf["hidden_dims"],
        )
        model.load_state_dict(torch.load(
            f"{MODELS_DIR}/vae_best.pt", map_location="cpu"
        ))
        model.eval()
        _vae_model  = model
        _vae_loaded = True
        print("[SHAP] VAE chargé pour l'explicabilité")
    except Exception as e:
        print(f"[SHAP] Impossible de charger le VAE : {e}")

# Charger au démarrage
_load_vae_once()

FEATURE_DISPLAY = {
    "year_established"               : "Année de création",
    "revenue"                        : "Chiffre d'affaires",
    "employees"                      : "Nombre d'employés",
    "has_subsidiary"                 : "Filiale",
    "sector_entertainment"           : "Secteur Entertainment",
    "sector_medical"                 : "Secteur Medical",
    "sector_retail"                  : "Secteur Retail",
    "sector_software"                : "Secteur Software",
    "sector_technolgy"               : "Secteur Technology",
    "office_location_Canada"         : "Localisation Canada",
    "office_location_France"         : "Localisation France",
    "office_location_Germany"        : "Localisation Allemagne",
    "office_location_United Kingdom" : "Localisation Royaume-Uni",
    "office_location_United States"  : "Localisation États-Unis",
}

@app.post("/explain/{doc_id}")
async def explain(doc_id: str):
    """
    Explication SHAP-like par décomposition de l'erreur de reconstruction VAE.
    Pour chaque feature i : contribution_i = (x_i - x_hat_i)^2
    Normalisé en pourcentage du score total.
    """
    if not _vae_loaded or _vae_model is None:
        return JSONResponse({"error": "VAE non disponible"}, status_code=503)

    # Récupérer le doc MongoDB
    try:
        from bson import ObjectId as ObjId
        doc = logs.find_one({"_id": ObjId(doc_id)})
        if not doc:
            return JSONResponse({"error": "Document introuvable"}, status_code=404)
    except Exception:
        return JSONResponse({"error": "ID invalide"}, status_code=400)

    # Reconstruire le vecteur depuis le doc
    msg = {
        "year_established": doc.get("year_established", 2000),
        "revenue"         : doc.get("revenue", 0.0),
        "employees"       : doc.get("employees", 1),
        "subsidiary_of"   : doc.get("subsidiary_of"),
        "sector"          : doc.get("sector", ""),
        "office_location" : doc.get("office_location", ""),
    }

    SECTOR_COLS   = ['sector_entertainment','sector_medical',
                     'sector_retail','sector_software','sector_technolgy']
    LOCATION_COLS = ['office_location_Canada','office_location_France',
                     'office_location_Germany','office_location_United Kingdom',
                     'office_location_United States']

    sector   = str(msg["sector"]).lower().strip()
    location = str(msg["office_location"]).strip()

    sector_ohe   = {c: 0.0 for c in SECTOR_COLS}
    if f"sector_{sector}" in sector_ohe:
        sector_ohe[f"sector_{sector}"] = 1.0

    location_ohe = {c: 0.0 for c in LOCATION_COLS}
    if f"office_location_{location}" in location_ohe:
        location_ohe[f"office_location_{location}"] = 1.0

    row = {
        "year_established": float(msg["year_established"]),
        "revenue"         : float(msg["revenue"]),
        "employees"       : float(msg["employees"]),
        "has_subsidiary"  : 1.0 if msg["subsidiary_of"] else 0.0,
        **sector_ohe,
        **location_ohe,
    }

    x_raw    = np.array([row.get(c, 0.0) for c in _vae_features],
                        dtype=np.float32).reshape(1, -1)
    x_scaled = _vae_scaler.transform(x_raw).astype(np.float32)

    # Inférence VAE
    with torch.no_grad():
        x_t   = torch.FloatTensor(x_scaled)
        x_hat, _ = _vae_model(x_t)
        x_np  = x_t.numpy()[0]
        xh_np = x_hat.numpy()[0]

    # Contributions par feature : erreur quadratique par dimension
    contrib    = (x_np - xh_np) ** 2
    total      = contrib.sum()
    pct        = (contrib / max(total, 1e-10)) * 100

    # Top features uniquement (contribution > 1%)
    features = []
    for i, fname in enumerate(_vae_features):
        features.append({
            "feature"      : fname,
            "label"        : FEATURE_DISPLAY.get(fname, fname),
            "contribution" : float(pct[i]),
            "raw_error"    : float(contrib[i]),
            "x_original"   : float(x_np[i]),
            "x_reconstructed": float(xh_np[i]),
        })

    features.sort(key=lambda f: f["contribution"], reverse=True)
    top_features = [f for f in features if f["contribution"] > 0.5][:8]

    # Verdict explicatif
    top1 = top_features[0] if top_features else None
    explanation = ""
    if top1:
        pct1 = top1["contribution"]
        explanation = (
            f"La feature '{top1['label']}' contribue à {pct1:.1f}% du score d'anomalie. "
            f"Le VAE a reconstruit une valeur significativement différente de l'originale, "
            f"ce qui indique que cette caractéristique est la principale source de déviation "
            f"par rapport aux profils normaux appris."
        )

    return {
        "doc_id"        : doc_id,
        "score"         : doc.get("score", 0),
        "total_error"   : float(total),
        "features"      : top_features,
        "explanation"   : explanation,
        "method"        : "VAE Reconstruction Error Decomposition",
        "n_features"    : len(_vae_features),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0", "timestamp": datetime.utcnow().isoformat()}


@app.get("/export")
async def export_csv():
    """Export CSV de tous les logs."""
    docs = list(logs.find({}, {"_id": 0}).sort("detected_at", -1).limit(10000))
    for d in docs:
        if "detected_at" in d and hasattr(d["detected_at"], "isoformat"):
            d["detected_at"] = d["detected_at"].isoformat()
    return docs


# ── Lancement ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_api:app", host="127.0.0.1", port=8000, reload=True)