def rows_to_dicts(cursor) -> list[dict]:
    rows = cursor.fetchall()
    if not rows:
        return []
    if hasattr(rows[0], "keys"):
        return [dict(r) for r in rows]
    if cursor.description:
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in rows]
    return []


def row_to_dict(cursor) -> dict | None:
    row = cursor.fetchone()
    if row is None:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    if cursor.description:
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    return None
