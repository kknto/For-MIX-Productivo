from app_db_migrations import apply_store_schema_migrations
from app_db_schema import build_store_schema_sql
from app_db_seed import seed_store_defaults


def initialize_store_database(store) -> None:
    with store._conn() as conn:
        conn.executescript(build_store_schema_sql(store))
        apply_store_schema_migrations(store, conn)
        seed_store_defaults(store, conn)
