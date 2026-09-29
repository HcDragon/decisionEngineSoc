"""
Database Seeder Script.
Initializes tables and seeds initial system telemetry and verification data.
"""
import logging
from datetime import datetime, timezone, timedelta
from soc.backend.app.db.session import SessionLocal, init_db
from soc.backend.app.db.models import Counter, Incident, IncidentStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("soc.seeder")


def seed_data() -> None:
    """Seed initial records and verify database readiness."""
    logger.info("Initializing database schema...")
    init_db()

    db = SessionLocal()
    try:
        # Check if already seeded
        existing_counter = db.query(Counter).first()
        if existing_counter:
            logger.info("Database already seeded with initial records. Skipping.")
            return

        now = datetime.now(timezone.utc)
        # Seed initial benign counter buckets for the past hour
        for i in range(5):
            bucket_time = (now - timedelta(minutes=i * 10)).replace(second=0, microsecond=0)
            db.add(Counter(ts_bucket=bucket_time, label="Benign Traffic", count=120 + i * 15))

        db.commit()
        logger.info("Database successfully seeded with initial baseline counters.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
