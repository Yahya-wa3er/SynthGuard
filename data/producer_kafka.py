"""
SynthGuard — data/kafka_producer.py
=====================================
Lit la table client_accounts depuis PostgreSQL
et envoie chaque ligne dans Kafka pour simuler
un flux de donnees temps reel.

Auteur  : El Houti Tlemcani Yahya
Projet  : SynthGuard — Detection d'anomalies B2B
Semaine : S8
"""

import json
import time
import signal
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from kafka import KafkaProducer
from kafka.errors import KafkaConnectionError, KafkaTimeoutError

# ═══════════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
DB_URL = "postgresql://user:password@localhost:5432/synthguard"
KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC = "synthguard-transactions"

# Delai entre chaque message (simule un flux temps reel)
# 0.001 = 1000 msg/sec  |  0.01 = 100 msg/sec  |  0.1 = 10 msg/sec
SEND_DELAY_SEC = 0.005

# Taille des blocs lus depuis PostgreSQL
READ_CHUNK = 1_000

# Nombre max de messages a envoyer (None = tout le dataset)
MAX_MESSAGES = None

# ═══════════════════════════════════════════════════════════════════════════════
# 1. GESTION ARRET PROPRE
# ═══════════════════════════════════════════════════════════════════════════════
running = True


def handle_signal(sig, frame):
    global running
    print(f"\n[Producer] Signal recu — arret propre en cours...")
    running = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. INITIALISATION
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("  SynthGuard — Kafka Producer")
print("=" * 60)

# Connexion PostgreSQL
engine = create_engine(DB_URL, pool_pre_ping=True)


# Connexion Kafka avec retry
def create_producer(retries=5, delay=3):
    for attempt in range(1, retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",  # attendre confirmation
                retries=3,
                max_block_ms=10_000,
            )
            print(f"  -> Kafka connecte : {KAFKA_BOOTSTRAP}")
            return producer
        except KafkaConnectionError as e:
            print(f"  [!] Tentative {attempt}/{retries} echouee : {e}")
            if attempt < retries:
                time.sleep(delay)
    print("  [!] Impossible de connecter a Kafka — arret")
    sys.exit(1)


producer = create_producer()

# ═══════════════════════════════════════════════════════════════════════════════
# 3. LECTURE POSTGRESQL ET ENVOI KAFKA
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n  Topic        : {TOPIC}")
print(f"  Delai/msg    : {SEND_DELAY_SEC}s ({int(1 / SEND_DELAY_SEC)} msg/s)")
print(f"  Max messages : {MAX_MESSAGES or 'illimite'}")
print(f"\n  Demarrage du flux...\n")

total_sent = 0
total_anom = 0
t_start = time.time()
t_last_log = t_start

try:
    with engine.connect() as conn:
        # Lecture par blocs pour eviter de charger 505k lignes en memoire
        offset = 0
        while running:
            query = text(f"""
                SELECT account, sector, year_established, revenue,
                       employees, office_location, subsidiary_of,
                       label, anomaly_type
                FROM client_accounts
                ORDER BY id
                LIMIT {READ_CHUNK} OFFSET {offset}
            """)
            df_chunk = pd.read_sql(query, conn)

            if df_chunk.empty:
                print(f"\n  [Producer] Dataset complet envoye — redemarrage")
                offset = 0
                continue

            for _, row in df_chunk.iterrows():
                if not running:
                    break
                if MAX_MESSAGES and total_sent >= MAX_MESSAGES:
                    running = False
                    break

                # Serialiser la ligne en dict JSON
                msg = {
                    "account": str(row["account"]),
                    "sector": str(row["sector"]),
                    "year_established": int(row["year_established"]),
                    "revenue": float(row["revenue"]),
                    "employees": int(row["employees"]),
                    "office_location": str(row["office_location"]),
                    "subsidiary_of": None if pd.isna(row["subsidiary_of"])
                    else str(row["subsidiary_of"]),
                    "label": int(row["label"]),
                    "anomaly_type": int(row["anomaly_type"]),
                    "timestamp": time.time(),
                }

                try:
                    producer.send(TOPIC, value=msg)
                    total_sent += 1
                    if row["label"] == 1:
                        total_anom += 1
                except KafkaTimeoutError as e:
                    print(f"  [!] Timeout envoi : {e}")
                    time.sleep(1)

                # Log toutes les 30 secondes
                now = time.time()
                if now - t_last_log >= 30:
                    elapsed = now - t_start
                    rate = total_sent / elapsed
                    print(
                        f"  [Producer] {total_sent:>8,} msgs envoyes | "
                        f"{total_anom:>6,} anomalies | "
                        f"{rate:.0f} msg/s | "
                        f"{elapsed:.0f}s"
                    )
                    t_last_log = now

                time.sleep(SEND_DELAY_SEC)
            offset += READ_CHUNK

except KeyboardInterrupt:
    pass

finally:
    producer.flush()
    producer.close()
    elapsed = time.time() - t_start
    print(f"\n  [Producer] Arret propre")
    print(f"  Messages envoyes : {total_sent:,}")
    print(f"  Anomalies        : {total_anom:,} ({total_anom / max(total_sent, 1) * 100:.2f}%)")
    print(f"  Duree            : {elapsed:.1f}s")