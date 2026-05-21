from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.auth import extract_auth_context, require_authenticated_user

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "route_manifest.json"
SUPPORTED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def _load_manifest() -> List[Dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        return []
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    routes = payload.get("routes")
    if not isinstance(routes, list):
        return []
    return [item for item in routes if isinstance(item, dict) and "path" in item]


def _build_handler(route: Dict[str, Any]) -> Callable:
    async def handler(request: Request) -> JSONResponse:
        auth = extract_auth_context(request)
        return JSONResponse(
            status_code=200,
            content={
                "status": "stub",
                "message": "Recovered route scaffold. Implement business logic.",
                "route": route.get("path"),
                "access": route.get("access"),
                "method": request.method,
                "query": dict(request.query_params),
                "path_params": dict(request.path_params),
                "authenticated": auth.authenticated,
            },
        )

    return handler


def build_api_router() -> APIRouter:
    router = APIRouter(prefix="/api/v2", tags=["recovery"])
    routes = _load_manifest()

    for route in routes:
        path = str(route.get("path", "")).strip()
        if not path:
            continue

        access = route.get("access", "public")
        dependencies = []
        if access == "auth":
            dependencies.append(Depends(require_authenticated_user))

        handler = _build_handler(route)
        tags = [str(route.get("tag", "misc"))]

        router.add_api_route(
            path=path,
            endpoint=handler,
            methods=SUPPORTED_METHODS,
            tags=tags,
            name=f"stub_{path.strip('/').replace('/', '_') or 'root'}",
            dependencies=dependencies,
        )

    @router.get("", tags=["meta"])
    async def api_root() -> Dict[str, Any]:
        return {
            "service": "keble.backend recovery scaffold",
            "version": "0.1.0",
            "routes_loaded": len(routes),
        }

    @router.get("/_meta/routes", tags=["meta"])
    async def route_manifest() -> Dict[str, Any]:
        return {"count": len(routes), "routes": routes}

    @router.get("/_meta/summary", tags=["meta"])
    async def route_summary() -> Dict[str, Any]:
        by_access: Dict[str, int] = {}
        by_tag: Dict[str, int] = {}
        for item in routes:
            access = str(item.get("access", "public"))
            tag = str(item.get("tag", "misc"))
            by_access[access] = by_access.get(access, 0) + 1
            by_tag[tag] = by_tag.get(tag, 0) + 1
        return {"count": len(routes), "by_access": by_access, "by_tag": by_tag}

    return router

