from pathlib import Path
import ast

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in minimal local envs
    yaml = None


BASE_DIR = Path(__file__).resolve().parents[2]

def _parse_scalar(value: str):
    cleaned = value.split(" #", 1)[0].strip()
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


def _simple_yaml_load(raw_text: str):
    root = {}
    stack = [(-1, root)]

    for raw_line in raw_text.splitlines():
        line_without_comment = raw_line.split(" #", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, _, value = line_without_comment.partition(":")
        key = key.strip()
        value = value.strip()

        while indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if value == "":
            nested = {}
            parent[key] = nested
            stack.append((indent, nested))
        else:
            parent[key] = _parse_scalar(value)

    return root


def load_settings(config_path: str = "config/settings.yaml"):
    resolved_path = Path(config_path)
    if not resolved_path.is_absolute():
        resolved_path = BASE_DIR / resolved_path

    raw_text = resolved_path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(raw_text)
    return _simple_yaml_load(raw_text)

settings = load_settings()
