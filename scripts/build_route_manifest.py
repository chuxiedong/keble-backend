from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parents[1]
FORENSICS = ROOT.parent / "forensics"
OUT_FILE = ROOT / "app" / "route_manifest.json"

SOURCES = [
    FORENSICS / "v2-endpoints.json",
    FORENSICS / "v2-crawl-endpoints.txt",
]


def _strip_api_prefix(path: str) -> str:
    if path.startswith("/api/v2/"):
        return path[len("/api/v2") :]
    if path == "/api/v2":
        return "/"
    return path


def _normalize_colon_params(path: str) -> str:
    segments = []
    for part in path.split("/"):
        if part.startswith(":") and len(part) > 1:
            segments.append("{" + part[1:] + "}")
        else:
            segments.append(part)
    return "/".join(segments)


def normalize_path(raw: str) -> str | None:
    if not raw:
        return None
    path = raw.strip()
    if not path:
        return None

    path = path.split("?", 1)[0].split("#", 1)[0].strip()
    if not path:
        return None

    if not path.startswith("/"):
        path = "/" + path

    path = _strip_api_prefix(path)
    path = _normalize_colon_params(path)
    path = re.sub(r"/{2,}", "/", path)

    if len(path) > 1:
        path = path.rstrip("/")

    if not path.startswith("/"):
        path = "/" + path

    return path


def infer_access(path: str) -> str:
    if "/public/" in path:
        return "public"
    if "/optional-owner/" in path:
        return "optional_owner"
    if "/owner/" in path or "/user/" in path:
        return "auth"
    return "public"


def infer_tag(path: str) -> str:
    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return "misc"
    if parts[0] == "features" and len(parts) > 1:
        return f"features_{parts[1]}"
    return parts[0]


def load_endpoints() -> Dict[str, Set[str]]:
    endpoint_sources: Dict[str, Set[str]] = defaultdict(set)

    json_path = SOURCES[0]
    if json_path.exists():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            for item in payload:
                raw = item if isinstance(item, str) else item.get("path")
                if not isinstance(raw, str):
                    continue
                endpoint_sources[raw].add(json_path.name)

    txt_path = SOURCES[1]
    if txt_path.exists():
        for line in txt_path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if raw:
                endpoint_sources[raw].add(txt_path.name)

    merged: Dict[str, Set[str]] = defaultdict(set)
    for raw, source_names in endpoint_sources.items():
        norm = normalize_path(raw)
        if not norm:
            continue
        merged[norm].update(source_names)

    return merged


def build_routes(merged: Dict[str, Set[str]]) -> List[dict]:
    routes: List[dict] = []
    for path, sources in sorted(merged.items()):
        route = {
            "path": path,
            "access": infer_access(path),
            "tag": infer_tag(path),
            "sources": sorted(sources),
        }
        routes.append(route)
    return routes


def print_summary(routes: Iterable[dict]) -> None:
    by_access: Dict[str, int] = defaultdict(int)
    by_tag: Dict[str, int] = defaultdict(int)
    count = 0

    for route in routes:
        count += 1
        by_access[str(route["access"])] += 1
        by_tag[str(route["tag"])] += 1

    print(f"routes: {count}")
    print("by_access:")
    for key in sorted(by_access):
        print(f"  {key}: {by_access[key]}")
    print("top_tags:")
    for key, value in sorted(by_tag.items(), key=lambda item: (-item[1], item[0]))[:12]:
        print(f"  {key}: {value}")


def main() -> None:
    merged = load_endpoints()
    routes = build_routes(merged)

    output = {"count": len(routes), "routes": routes}
    OUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"manifest: {OUT_FILE}")
    print_summary(routes)


if __name__ == "__main__":
    main()

