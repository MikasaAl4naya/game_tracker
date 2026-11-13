import sys
from database import SyncSessionLocal
from sqlalchemy import text

def run_migration():
    db = SyncSessionLocal()
    try:
        print("Checking if platform column exists...")
        db.execute(text("ALTER TABLE price_results ADD COLUMN IF NOT EXISTS platform VARCHAR DEFAULT 'Steam';"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_price_results_platform ON price_results (platform);"))
        db.execute(text("UPDATE price_results SET platform = 'Steam' WHERE platform IS NULL;"))
        db.commit()
        print("Migration completed successfully!")
        
        # Verify
        res = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'price_results';")).fetchall()
        print("Columns in price_results:", [f"{r[0]} ({r[1]})" for r in res])
    except Exception as e:
        db.rollback()
        print("Error during migration:", e)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
