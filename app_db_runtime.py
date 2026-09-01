import re


class SQLiteWrapper:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            self.conn.close()

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self.conn, name)


class PGWrapper:
    def __init__(self, conn, pool, cursor_factory):
        self.conn = conn
        self.pool = pool
        self.cursor_factory = cursor_factory

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
            else:
                try:
                    self.conn.commit()
                except Exception:
                    pass
        finally:
            if self.pool:
                try:
                    if getattr(self.conn, "closed", 0) != 0:
                        self.pool.putconn(self.conn, close=True)
                    else:
                        self.pool.putconn(self.conn)
                except Exception:
                    pass
            else:
                try:
                    self.conn.close()
                except Exception:
                    pass

    def execute(self, sql, params=()):
        cur = self.conn.cursor(cursor_factory=self.cursor_factory)
        query = sql.replace("?", "%s")
        if "INSERT OR IGNORE" in query.upper():
            query = query.replace("INSERT OR IGNORE", "INSERT")
            match = re.search(r"INTO\s+(\w+)", query, re.IGNORECASE)
            if match:
                table = match.group(1).lower()
                keys = {"users": "username", "datasets": "name", "app_state": "key", "remisiones": "remision_no"}
                if table in keys:
                    query += f" ON CONFLICT ({keys[table]}) DO NOTHING"
        if "INTEGER PRIMARY KEY AUTOINCREMENT" in query.upper():
            query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        if "REAL" in query.upper() and "DOUBLE PRECISION" not in query.upper():
            query = query.replace("REAL", "DOUBLE PRECISION")
        cur.execute(query, params)
        return cur

    def executescript(self, sql):
        with self.conn.cursor() as cur:
            for statement in sql.split(";"):
                if statement.strip():
                    self.execute(statement)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def wrap_sqlite_conn(sqlite_conn):
    return SQLiteWrapper(sqlite_conn)


def wrap_pg_conn(pg_conn, pool, cursor_factory):
    return PGWrapper(pg_conn, pool=pool, cursor_factory=cursor_factory)


def columns(conn, table_name: str, is_postgres: bool) -> set[str]:
    if is_postgres:
        with conn.conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (table_name.lower(),),
            )
            return {row[0] for row in cur.fetchall()}
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def ensure_column(conn, table_name: str, column_name: str, ddl: str, is_postgres: bool):
    if column_name in columns(conn, table_name, is_postgres=is_postgres):
        return
    if is_postgres:
        ddl = ddl.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY").replace(
            "REAL", "DOUBLE PRECISION"
        )
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")
