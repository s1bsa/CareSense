import os
import re
import ast
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in minimal local envs
    yaml = None


BASE_DIR = Path(__file__).resolve().parents[2]


def _parse_scalar(value):
    cleaned = value.strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return ast.literal_eval(cleaned)
    except (ValueError, SyntaxError):
        try:
            return int(cleaned)
        except ValueError:
            try:
                return float(cleaned)
            except ValueError:
                return cleaned.strip('"').strip("'")


def _simple_yaml_load(raw_text):
    root = {}
    stack = [(-1, root)]
    lines = raw_text.splitlines()

    for index, raw_line in enumerate(lines):
        line_without_comment = raw_line.split(" #", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = line_without_comment.strip()

        while indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if stripped.startswith("- "):
            value = _parse_scalar(stripped[2:])
            if not isinstance(parent, list):
                raise ValueError("Invalid YAML structure for fallback parser")
            parent.append(value)
            continue

        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()

        if value == "":
            next_container = []
            for future_line in lines[index + 1:]:
                future = future_line.split(" #", 1)[0].strip()
                if not future:
                    continue
                future_indent = len(future_line) - len(future_line.lstrip(" "))
                if future_indent <= indent:
                    next_container = {}
                    break
                next_container = [] if future.startswith("- ") else {}
                break

            parent[key] = next_container
            stack.append((indent, next_container))
        else:
            parent[key] = _parse_scalar(value)

    return root


def load_yaml(path):
    resolved_path = Path(path)
    if not resolved_path.is_absolute():
        resolved_path = BASE_DIR / resolved_path

    if not resolved_path.exists():
        return {}

    content = resolved_path.read_text(encoding="utf-8")
    
    def env_var_replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    
    content = re.sub(r'\$\{([^}]+)\}', env_var_replacer, content)
    if yaml is not None:
        return yaml.safe_load(content)
    return _simple_yaml_load(content)

settings = load_yaml("config/settings.yaml")
symptoms = load_yaml("config/symptoms.yaml").get('keywords', [])
