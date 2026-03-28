from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List


_PLACEHOLDER_RE = re.compile(r'\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}')


def nested_get(data: Any, dotted: str, default: Any = None) -> Any:
    if dotted in ('', '.', None):
        return data
    node = data
    for raw_part in dotted.split('.'):
        part = raw_part.strip()
        if part == '':
            continue
        if isinstance(node, dict):
            node = node.get(part)
        elif isinstance(node, list) and part.isdigit():
            idx = int(part)
            if idx < 0 or idx >= len(node):
                return default
            node = node[idx]
        else:
            return default
        if node is None:
            return default
    return node


def first_non_empty_path(data: Any, dotted_paths: Iterable[str]) -> Any:
    for path in dotted_paths:
        value = nested_get(data, path)
        if value not in (None, '', [], {}):
            return value
    return None


def render_template_string(text: str, context: Dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = nested_get(context, key, '')
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return '' if value is None else str(value)
    return _PLACEHOLDER_RE.sub(repl, text)


def render_template_obj(obj: Any, context: Dict[str, Any]) -> Any:
    if isinstance(obj, str):
        return render_template_string(obj, context)
    if isinstance(obj, list):
        return [render_template_obj(item, context) for item in obj]
    if isinstance(obj, dict):
        return {k: render_template_obj(v, context) for k, v in obj.items()}
    return obj


def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
