from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./gym.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Colunas novas adicionadas em tabelas já existentes. O projeto não usa Alembic
# (`Base.metadata.create_all` só cria tabelas novas, não altera existentes), então
# aplicamos aqui um ALTER TABLE idempotente para não exigir apagar o gym.db a cada release.
_STARTUP_COLUMN_MIGRATIONS = {
    "exercises": [("rest_seconds_target", "INTEGER")],
    "workouts": [
        ("live_session_started_at", "DATETIME"),
        ("live_session_finished_at", "DATETIME"),
    ],
}

def run_startup_migrations() -> None:
    with engine.connect() as conn:
        for table, columns in _STARTUP_COLUMN_MIGRATIONS.items():
            existing_columns = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            for column_name, column_type in columns:
                if column_name not in existing_columns:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")
        conn.commit()