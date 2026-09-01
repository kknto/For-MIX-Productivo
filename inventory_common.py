def row_to_dict(cursor) -> dict | None:
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    if hasattr(cursor, "description") and cursor.description:
        cols = [col[0] for col in cursor.description]
        return dict(zip(cols, row))
    return None


def rows_to_dicts(cursor) -> list[dict]:
    rows = cursor.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return [dict(r) for r in rows]
    if hasattr(cursor, "description") and cursor.description:
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, r)) for r in rows]
    return []
