import json


def decode_json_payload(body: bytes) -> dict:
    last = None
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return json.loads(body.decode(enc))
        except Exception as exc:
            last = exc
    raise ValueError(f"Invalid JSON payload: {last}")
