from __future__ import annotations

import os
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

try:
    import pymysql  # type: ignore
except Exception:
    pymysql = None


def parse_mysql_dsn(dsn: str) -> Dict[str, Any]:
    parsed = urlparse(dsn)
    qs = parse_qs(parsed.query)
    return {
        'host': parsed.hostname or '127.0.0.1',
        'port': parsed.port or 3306,
        'user': parsed.username,
        'password': parsed.password,
        'database': (parsed.path or '/').lstrip('/'),
        'charset': qs.get('charset', ['utf8mb4'])[0],
        'autocommit': True,
    }


def get_mysql_dsn(explicit: Optional[str] = None) -> Optional[str]:
    return explicit or os.getenv('MYSQL_DSN') or None


def connect_mysql(dsn: Optional[str] = None):
    final_dsn = get_mysql_dsn(dsn)
    if not final_dsn:
        return None
    if pymysql is None:
        raise RuntimeError('pymysql is not installed but MYSQL_DSN was provided')
    return pymysql.connect(**parse_mysql_dsn(final_dsn))
