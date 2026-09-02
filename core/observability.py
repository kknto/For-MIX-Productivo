import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone

from flask import g, request, session


SENSITIVE_PATTERNS = (
    re.compile(r"postgres(?:ql)?://[^\s\"']+", re.IGNORECASE),
    re.compile(r"mysql://[^\s\"']+", re.IGNORECASE),
    re.compile(r"sqlite:///[^\s\"']+", re.IGNORECASE),
    re.compile(r"(password|passwd|secret|token|api[_-]?key)=([^&\s]+)", re.IGNORECASE),
)


def redact_sensitive(value: str) -> str:
    redacted = value
    for pattern in SENSITIVE_PATTERNS:
        if pattern.groups >= 2:
            redacted = pattern.sub(lambda match: f"{match.group(1)}=***", redacted)
        else:
            redacted = pattern.sub("***", redacted)
    return redacted


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive(record.getMessage()),
        }
        for key in ("request_id", "method", "path", "status", "latency_ms", "user", "role", "origin", "host"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = redact_sensitive(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    app.logger.handlers.clear()
    app.logger.propagate = True
    app.logger.setLevel(level)


def request_id():
    return getattr(g, "request_id", "")


def install_request_logging(app):
    @app.before_request
    def start_request_log():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        g.request_started_at = time.perf_counter()

    @app.after_request
    def finish_request_log(response):
        response.headers["X-Request-ID"] = request_id()
        started_at = getattr(g, "request_started_at", time.perf_counter())
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        app.logger.info(
            "request.complete",
            extra={
                "request_id": request_id(),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "user": session.get("username"),
                "role": session.get("role"),
            },
        )
        return response
