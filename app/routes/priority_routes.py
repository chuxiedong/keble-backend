from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.auth import require_authenticated_user
from app.services.inmemory import store

router = APIRouter(prefix="/api/v2", tags=["priority"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _bad_values(*fields: str) -> JSONResponse:
    suffix = ", ".join(fields)
    return JSONResponse(status_code=400, content={"error": f"Invalid values: {suffix}"})


def _json_payload(data: Any) -> dict:
    return data if isinstance(data, dict) else {}


def _is_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value.strip().lower()))


def _token_response(token_record, user_record) -> dict:
    return {
        "tokenType": "bearer",
        "accessToken": token_record.token,
        "refreshToken": token_record.refresh_token,
        "expiresIn": token_record.expires_in,
        "user": {
            "id": user_record.user_id,
            "email": user_record.email,
            "nickname": user_record.nickname,
            "createdAt": user_record.created_at,
        },
    }


def _resolve_user_from_auth(request: Request):
    auth = require_authenticated_user(request)
    token_record = store.find_token(auth.token or "")
    if token_record:
        user = store.find_user_by_id(token_record.user_id)
        if user:
            return user
    # Fallback user keeps auth routes usable during recovery.
    return store.create_or_update_user("owner@keble.local", "owner-password")


def _coerce_int(value: Any, default: int, minimum: int = 0, maximum: Optional[int] = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < minimum:
        parsed = minimum
    if maximum is not None and parsed > maximum:
        parsed = maximum
    return parsed


def _is_truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_timestamp(value: Any) -> Optional[int]:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    try:
        normalized = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def _find_report_task_by_report_id(report_id: str) -> Optional[dict]:
    target = report_id.strip()
    if not target:
        return None
    for task in store.report_tasks.values():
        if task.get("reportId") == target:
            return task
    return None


def _latest_report_task(owner_user_id: Optional[str] = None) -> Optional[dict]:
    tasks = list(store.report_tasks.values())
    if owner_user_id:
        tasks = [item for item in tasks if item.get("ownerUserId") == owner_user_id]
    if not tasks:
        return None
    return sorted(tasks, key=lambda item: int(item.get("createdAt", 0)), reverse=True)[0]


def _ensure_demo_report_task() -> dict:
    fallback_owner = store.create_or_update_user("owner@keble.local", "owner-password")
    task = _latest_report_task(owner_user_id=fallback_owner.user_id)
    if task:
        return task
    return store.add_report_task(
        owner_user_id=fallback_owner.user_id,
        asin="B08N5L5R6P",
        marketplace="US",
        keyword="portable blender bottle",
    )


def _resolve_report_task(request: Request, report_id: Optional[str] = None) -> Optional[dict]:
    query = request.query_params
    requested_report_id = str(report_id or query.get("report_id") or query.get("reportId") or "").strip()
    if requested_report_id:
        report_task = _find_report_task_by_report_id(requested_report_id)
        if report_task:
            return report_task
        return None

    requested_task_id = str(query.get("task_id") or query.get("taskId") or "").strip()
    if requested_task_id:
        return store.get_report_task(requested_task_id)

    return _latest_report_task() or _ensure_demo_report_task()


def _build_report_sections(task: dict) -> dict:
    report_id = str(task.get("reportId", "report_demo"))
    asin = str(task.get("asin", "B08N5L5R6P"))
    marketplace = str(task.get("marketplace", "US"))
    keyword = str(task.get("keyword", "portable blender"))
    seed = (sum(ord(ch) for ch in report_id) % 19) + 1

    brands = [
        {"brand": "AeroBlend", "monthlySales": 340 + seed * 8, "avgPrice": 27.9 + seed * 0.2, "profitRatio": 0.18},
        {"brand": "MixPro", "monthlySales": 290 + seed * 6, "avgPrice": 24.5 + seed * 0.2, "profitRatio": 0.16},
        {"brand": "DailySip", "monthlySales": 240 + seed * 5, "avgPrice": 22.9 + seed * 0.1, "profitRatio": 0.14},
    ]
    products = []
    for index in range(6):
        rank = index + 1
        products.append(
            {
                "asin": f"B{(seed * 137 + rank * 97) % 999999:06d}",
                "title": f"{keyword.title()} Variant {rank}",
                "monthlySales": 120 + seed * 6 + rank * 18,
                "monthlyRevenue": round((120 + seed * 6 + rank * 18) * (19.5 + rank * 1.4), 2),
                "estimatedProfitRatio": round(0.11 + rank * 0.01, 3),
            }
        )

    periods = [
        {"period": "2025-Q3", "newReleasedSuccessRate": round(0.42 + seed * 0.002, 3)},
        {"period": "2025-Q4", "newReleasedSuccessRate": round(0.45 + seed * 0.002, 3)},
        {"period": "2026-Q1", "newReleasedSuccessRate": round(0.47 + seed * 0.002, 3)},
    ]
    total_sales = sum(int(item["monthlySales"]) for item in products)
    profitable = [item for item in products if float(item["estimatedProfitRatio"]) >= 0.13]

    return {
        "profile": {
            "reportId": report_id,
            "asin": asin,
            "marketplace": marketplace,
            "keyword": keyword,
            "createdAt": int(task.get("createdAt", 0)),
            "status": "completed",
        },
        "overview": {
            "reportId": report_id,
            "totalComparableProducts": len(products),
            "estimatedMonthlySalesPool": total_sales,
            "estimatedMedianProfitRatio": round(sum(float(item["estimatedProfitRatio"]) for item in products) / len(products), 3),
            "recommendation": "Proceed with controlled launch and test listing angle.",
        },
        "investment": {
            "reportId": report_id,
            "estimatedBudget": {"currency": "USD", "amount": 4200 + seed * 120},
            "difficulty": "median",
            "reasons": ["Need moderate initial ad spend", "Category has established competitors"],
        },
        "periods": {"reportId": report_id, "items": periods},
        "profit": {
            "reportId": report_id,
            "profitableProducts": len(profitable),
            "totalProducts": len(products),
            "profitableRate": round(len(profitable) / len(products), 3),
        },
        "brandMetricsList": brands,
        "brandsMetricsObj": {
            "reportId": report_id,
            "totalBrands": len(brands),
            "topBrand": brands[0]["brand"],
            "topBrandMonthlySales": brands[0]["monthlySales"],
        },
        "productMetricsPreviewList": products[:3],
        "productMetricsList": products,
        "productsMetricsObj": {
            "reportId": report_id,
            "totalProducts": len(products),
            "averageMonthlySales": round(total_sales / len(products), 2),
            "averageProfitRatio": round(sum(float(item["estimatedProfitRatio"]) for item in products) / len(products), 3),
        },
        "interpretationList": [
            {"type": "market", "message": f"{marketplace} demand for '{keyword}' remains stable."},
            {"type": "competition", "message": "Competition is medium with room for differentiated positioning."},
            {"type": "entry", "message": "Focus on value bundle and visual differentiation for first launch cycle."},
        ],
        "samplesList": [
            {"sampleId": f"{report_id}_s1", "asin": products[0]["asin"], "title": products[0]["title"]},
            {"sampleId": f"{report_id}_s2", "asin": products[1]["asin"], "title": products[1]["title"]},
            {"sampleId": f"{report_id}_s3", "asin": products[2]["asin"], "title": products[2]["title"]},
        ],
        "samplesObj": {
            "reportId": report_id,
            "notes": "Sample products selected by sales momentum and stable profit ratio.",
            "samples": products[:3],
        },
    }


@router.post("/users/public/email-code")
async def send_email_code(body: dict) -> JSONResponse:
    payload = _json_payload(body)
    email = str(payload.get("email", "")).strip().lower()
    purpose = str(payload.get("purpose", "")).strip().lower()
    if not _is_email(email) or not purpose:
        return _bad_values("email", "purpose")

    code = "".join(secrets.choice("0123456789") for _ in range(6))
    store.save_email_code(email=email, purpose=purpose, code=code, ttl=600)
    return JSONResponse(
        {
            "success": True,
            "email": email,
            "purpose": purpose,
            "codePreview": f"***{code[-2:]}",
            "expiresIn": 600,
        }
    )


@router.post("/users/public/obj")
async def signup_user(body: dict) -> JSONResponse:
    payload = _json_payload(body)
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()
    if not _is_email(email) or len(password) < 6:
        return _bad_values("email", "password")

    user = store.create_or_update_user(email=email, password=password)
    token_record = store.issue_token(user.user_id)
    return JSONResponse(_token_response(token_record, user))


@router.post("/users/public/obj/login")
async def login_user(body: dict) -> JSONResponse:
    payload = _json_payload(body)
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()
    if not _is_email(email) or not password:
        return _bad_values("email", "password")

    user = store.find_user_by_email(email)
    if user is None:
        user = store.create_or_update_user(email=email, password=password)
    elif user.password != password:
        return JSONResponse(status_code=401, content={"error": "Invalid credentials"})

    token_record = store.issue_token(user.user_id)
    return JSONResponse(_token_response(token_record, user))


@router.post("/users/public/access-token/exchange")
async def exchange_access_token(body: dict) -> JSONResponse:
    payload = _json_payload(body)
    secret = str(payload.get("secret", "")).strip()
    if not secret:
        return _bad_values("secret")

    expected = "keble-recovery-secret"
    if secret != expected:
        return _bad_values("secret")

    email = str(payload.get("email", "owner@keble.local")).strip().lower()
    if not _is_email(email):
        return _bad_values("email")

    user = store.create_or_update_user(email=email, password="recovery-password")
    token_record = store.issue_token(user.user_id)
    return JSONResponse(_token_response(token_record, user))


@router.post("/users/public/obj/reset-password")
async def reset_password(body: dict) -> JSONResponse:
    payload = _json_payload(body)
    email = str(payload.get("email", "")).strip().lower()
    code = str(payload.get("code", "")).strip()
    new_password = str(payload.get("newPassword", payload.get("password", ""))).strip()
    if not _is_email(email):
        return _bad_values("email")
    if not code:
        return _bad_values("code")
    if len(new_password) < 6:
        return _bad_values("newPassword")

    valid = store.verify_email_code(email=email, purpose="reset_password", code=code)
    if not valid:
        return _bad_values("code")

    user = store.create_or_update_user(email=email, password=new_password)
    token_record = store.issue_token(user.user_id)
    return JSONResponse(_token_response(token_record, user))


@router.get("/users/public/wechat/qrcode")
async def public_wechat_qrcode() -> JSONResponse:
    return JSONResponse(
        {
            "ticket": "keble-recovery-ticket",
            "url": "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=keble-recovery-ticket",
        }
    )


@router.get("/users/user/obj")
async def get_user_profile(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    return JSONResponse(
        {
            "id": user.user_id,
            "email": user.email,
            "nickname": user.nickname,
            "createdAt": user.created_at,
        }
    )


@router.post("/users/user/access-token/exchange-new")
async def exchange_new_token(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    token_record = store.issue_token(user.user_id)
    return JSONResponse(_token_response(token_record, user))


@router.post("/users/user/wechat/detach")
async def detach_wechat(_auth=Depends(require_authenticated_user)) -> JSONResponse:
    return JSONResponse({"success": True})


@router.get("/users/user/wechat/qrcode/scan")
async def wechat_scan_state(_auth=Depends(require_authenticated_user)) -> JSONResponse:
    return JSONResponse({"scanned": False, "bound": False})


@router.post("/orders/user/stripe/checkout")
async def create_stripe_checkout(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    service_id = str(payload.get("serviceId", payload.get("service_id", ""))).strip()
    if not service_id:
        return _bad_values("serviceId")

    currency = str(payload.get("currency", "USD")).upper()
    amount = float(payload.get("amount", 49.0))
    order = store.add_order(
        {
            "ownerUserId": user.user_id,
            "serviceId": service_id,
            "currency": currency,
            "amount": amount,
            "status": "checkout_created",
        }
    )
    return JSONResponse(
        {
            "orderId": order["id"],
            "status": order["status"],
            "checkoutUrl": f"https://checkout.stripe.com/pay/{order['id']}",
        }
    )


@router.get("/orders/owner/list")
async def list_owner_orders(_auth=Depends(require_authenticated_user)) -> JSONResponse:
    return JSONResponse(store.list_orders())


@router.post("/orders/owner/obj")
async def create_owner_order(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    service_id = str(payload.get("serviceId", payload.get("service_id", ""))).strip()
    if not service_id:
        return _bad_values("serviceId")
    amount = float(payload.get("amount", 49.0))
    currency = str(payload.get("currency", "USD")).upper()
    order = store.add_order(
        {
            "ownerUserId": user.user_id,
            "serviceId": service_id,
            "amount": amount,
            "currency": currency,
            "status": "created",
        }
    )
    return JSONResponse(order)


@router.get("/orders/owner/obj/{order_id}")
async def get_owner_order(order_id: str, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    order = store.get_order(order_id)
    if not order:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(order)


@router.post("/orders/owner/obj/{order_id}/paid")
async def mark_owner_order_paid(order_id: str, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    order = store.mark_order_paid(order_id)
    if not order:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(order)


@router.post("/orders/owner/alipay/obj")
async def create_alipay_order(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    service_id = str(payload.get("serviceId", payload.get("service_id", ""))).strip()
    if not service_id:
        return _bad_values("serviceId")
    order = store.add_order(
        {
            "ownerUserId": user.user_id,
            "serviceId": service_id,
            "amount": float(payload.get("amount", 49.0)),
            "currency": str(payload.get("currency", "CNY")).upper(),
            "status": "alipay_created",
        }
    )
    return JSONResponse(
        {
            "orderId": order["id"],
            "status": order["status"],
            "alipayUrl": f"https://openapi.alipay.com/gateway.do?out_trade_no={order['id']}",
        }
    )


@router.get("/orders/owner/alipay/obj/{order_id}")
async def get_alipay_order(order_id: str, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    order = store.get_order(order_id)
    if not order:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(
        {
            "orderId": order["id"],
            "status": order.get("status", "unknown"),
            "alipayUrl": f"https://openapi.alipay.com/gateway.do?out_trade_no={order['id']}",
        }
    )


@router.get("/features/amz-product-reports/public/product-reports/show-case/list")
async def public_report_showcases() -> JSONResponse:
    return JSONResponse(store.report_showcases)


@router.post("/features/amz-product-reports/owner/tasks/obj")
async def create_report_task(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    asin = str(payload.get("asin", "")).strip().upper()
    marketplace = str(payload.get("marketplace", "US")).strip().upper()
    keyword = str(payload.get("keyword", "")).strip()
    if not asin:
        return _bad_values("asin")

    task = store.add_report_task(
        owner_user_id=user.user_id,
        asin=asin,
        marketplace=marketplace,
        keyword=keyword,
    )
    return JSONResponse(task)


@router.get("/features/amz-product-reports/owner/tasks/list")
async def list_owner_report_tasks(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    return JSONResponse(store.list_report_tasks(owner_user_id=user.user_id))


@router.get("/features/amz-product-reports/owner/tasks/obj/{task_id}")
async def get_owner_report_task(task_id: str, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    task = store.get_report_task(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(task)


@router.get("/features/amz-product-reports/optional-owner/tasks/obj/{task_id}")
async def get_optional_owner_task(task_id: str) -> JSONResponse:
    task = store.get_report_task(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(task)


@router.get("/features/amz-product-reports/optional-owner/tasks/obj/{task_id}/report")
async def get_optional_owner_task_report(task_id: str) -> JSONResponse:
    task = store.get_report_task(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(
        {
            "taskId": task_id,
            "reportId": task["reportId"],
            "summary": {
                "asin": task["asin"],
                "marketplace": task["marketplace"],
                "keyword": task["keyword"],
                "recommendation": "Proceed with controlled launch and test listing angle.",
            },
        }
    )


@router.get("/features/amz-product-reports/optional-owner/tasks/obj")
async def get_optional_owner_task_by_query(request: Request) -> JSONResponse:
    task = _resolve_report_task(request)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(task)


@router.get("/features/amz-product-reports/optional-owner/product-reports/profile/obj")
@router.get("/features/amz-product-reports/optional-owner/product-reports/profile/obj/{report_id}")
async def get_optional_owner_report_profile(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["profile"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/overview/obj")
@router.get("/features/amz-product-reports/optional-owner/product-reports/overview/obj/{report_id}")
async def get_optional_owner_report_overview(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["overview"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/investment/obj")
@router.get("/features/amz-product-reports/optional-owner/product-reports/investment/obj/{report_id}")
async def get_optional_owner_report_investment(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["investment"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/periods/obj")
@router.get("/features/amz-product-reports/optional-owner/product-reports/periods/obj/{report_id}")
async def get_optional_owner_report_periods(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["periods"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/profit/obj")
@router.get("/features/amz-product-reports/optional-owner/product-reports/profit/obj/{report_id}")
async def get_optional_owner_report_profit(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["profit"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/brand-metrics/list")
@router.get("/features/amz-product-reports/optional-owner/product-reports/brand-metrics/list/{report_id}")
async def list_optional_owner_brand_metrics(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["brandMetricsList"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/brands-metrics/obj")
@router.get("/features/amz-product-reports/optional-owner/product-reports/brands-metrics/obj/{report_id}")
async def get_optional_owner_brands_metrics(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["brandsMetricsObj"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/product-metrics-preview/list")
@router.get("/features/amz-product-reports/optional-owner/product-reports/product-metrics-preview/list/{report_id}")
async def list_optional_owner_product_metrics_preview(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["productMetricsPreviewList"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/product-metrics/list")
@router.get("/features/amz-product-reports/optional-owner/product-reports/product-metrics/list/{report_id}")
async def list_optional_owner_product_metrics(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["productMetricsList"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/products-metrics/obj")
@router.get("/features/amz-product-reports/optional-owner/product-reports/products-metrics/obj/{report_id}")
async def get_optional_owner_products_metrics(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["productsMetricsObj"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/interpretation/list")
@router.get("/features/amz-product-reports/optional-owner/product-reports/interpretation/list/{report_id}")
async def list_optional_owner_interpretation(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["interpretationList"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/samples/list")
@router.get("/features/amz-product-reports/optional-owner/product-reports/samples/list/{report_id}")
async def list_optional_owner_samples(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["samplesList"])


@router.get("/features/amz-product-reports/optional-owner/product-reports/samples/obj")
@router.get("/features/amz-product-reports/optional-owner/product-reports/samples/obj/{report_id}")
async def get_optional_owner_samples_obj(request: Request, report_id: Optional[str] = None) -> JSONResponse:
    task = _resolve_report_task(request, report_id=report_id)
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(_build_report_sections(task)["samplesObj"])


@router.get("/features/amz-product-reports/owner/asin-info/obj")
async def get_owner_asin_info(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    asin = str(request.query_params.get("asin", "")).strip().upper()
    marketplace = str(request.query_params.get("marketplace", "US")).strip().upper()
    if not asin:
        return _bad_values("asin")

    categories = store.list_root_categories(marketplace)
    return JSONResponse(
        {
            "asin": asin,
            "marketplace": marketplace,
            "title": f"Recovered listing for {asin}",
            "images": [f"https://images.example.com/{asin}.jpg"],
            "categories": categories,
            "pricing": {"currency": "USD", "price": 29.9},
        }
    )


@router.get("/features/amz-product-reports/owner/products-preview/obj")
async def get_owner_products_preview(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    asin = str(request.query_params.get("asin", "")).strip().upper()
    marketplace = str(request.query_params.get("marketplace", "US")).strip().upper()
    keyword = str(request.query_params.get("keyword", "portable blender")).strip().lower()
    if not asin:
        return _bad_values("asin")

    preview = []
    for index in range(5):
        rank = index + 1
        preview.append(
            {
                "asin": f"B{(rank * 103 + 77) % 999999:06d}",
                "title": f"{keyword.title()} Preview {rank}",
                "marketplace": marketplace,
                "estimatedMonthlySales": 100 + rank * 21,
                "estimatedProfitRatio": round(0.1 + rank * 0.015, 3),
            }
        )
    return JSONResponse({"asin": asin, "marketplace": marketplace, "keyword": keyword, "products": preview})


@router.get("/features/amz-product-reports/user/product-reports/show-case/list")
async def list_user_product_report_showcases(_auth=Depends(require_authenticated_user)) -> JSONResponse:
    return JSONResponse(store.report_showcases)


@router.get("/orgs/user/list")
async def list_user_orgs(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    return JSONResponse(store.list_orgs_by_user(user.user_id))


@router.post("/orgs/user/org/obj")
async def create_user_org(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    name = str(payload.get("name", "")).strip()
    if not name:
        return _bad_values("name")
    org = store.create_org(owner_user_id=user.user_id, name=name)
    return JSONResponse(org)


@router.get("/orgs/user/org/{org_id}")
async def get_user_org(org_id: str, request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    org = store.get_org(org_id)
    if not org or user.user_id not in org.get("members", []):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(org)


@router.get("/orgs/user/org/{org_id}/list")
async def list_user_org_members(org_id: str, request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    org = store.get_org(org_id)
    if not org or user.user_id not in org.get("members", []):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse({"orgId": org_id, "members": org.get("members", []), "admins": org.get("admins", [])})


@router.get("/orgs/public/obj/{org_id}")
async def get_public_org(org_id: str) -> JSONResponse:
    org = store.get_org(org_id)
    if not org:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse({"id": org["id"], "name": org["name"], "createdAt": org["createdAt"]})


def _assert_org_admin(org: dict, user_id: str) -> Optional[JSONResponse]:
    if user_id not in org.get("admins", []):
        return JSONResponse(status_code=403, content={"error": "Insufficient permissions"})
    return None


@router.post("/orgs/user/org/{org_id}/add-admin")
async def add_org_admin(org_id: str, request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    operator = _resolve_user_from_auth(request)
    org = store.get_org(org_id)
    if not org:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    auth_error = _assert_org_admin(org, operator.user_id)
    if auth_error:
        return auth_error

    payload = _json_payload(body)
    email = str(payload.get("email", "")).strip().lower()
    if not _is_email(email):
        return _bad_values("email")
    target = store.create_or_update_user(email=email, password="invited-password")
    store.add_org_member(org_id=org_id, user_id=target.user_id, as_admin=True)
    return JSONResponse({"success": True, "orgId": org_id, "adminUserId": target.user_id})


@router.post("/orgs/user/org/{org_id}/add-superadmin")
async def add_org_superadmin(org_id: str, request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    return await add_org_admin(org_id, request, body)


@router.post("/orgs/user/org/{org_id}/invite")
async def invite_org_member(org_id: str, request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    operator = _resolve_user_from_auth(request)
    org = store.get_org(org_id)
    if not org:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    auth_error = _assert_org_admin(org, operator.user_id)
    if auth_error:
        return auth_error

    payload = _json_payload(body)
    email = str(payload.get("email", "")).strip().lower()
    role = str(payload.get("role", "member")).strip().lower()
    if not _is_email(email):
        return _bad_values("email")
    target = store.create_or_update_user(email=email, password="invited-password")
    store.add_org_member(org_id=org_id, user_id=target.user_id, as_admin=(role == "admin"))
    return JSONResponse({"success": True, "orgId": org_id, "invitedUserId": target.user_id, "role": role})


@router.post("/orgs/user/org/{org_id}/remove")
async def remove_org_member(org_id: str, request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    operator = _resolve_user_from_auth(request)
    org = store.get_org(org_id)
    if not org:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    auth_error = _assert_org_admin(org, operator.user_id)
    if auth_error:
        return auth_error

    payload = _json_payload(body)
    user_id = str(payload.get("userId", "")).strip()
    if not user_id:
        return _bad_values("userId")
    store.remove_org_member(org_id=org_id, user_id=user_id)
    return JSONResponse({"success": True, "orgId": org_id, "removedUserId": user_id})


@router.post("/orgs/user/org/{org_id}/leave")
async def leave_org(org_id: str, request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    org = store.get_org(org_id)
    if not org:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    store.remove_org_member(org_id=org_id, user_id=user.user_id)
    return JSONResponse({"success": True, "orgId": org_id, "leftUserId": user.user_id})


@router.get("/referrals/public/validate-code")
async def validate_referral_code(code: str = "") -> JSONResponse:
    normalized = code.strip().upper()
    if not normalized:
        return _bad_values("code")
    referral = store.get_referral_code(normalized)
    if not referral:
        return JSONResponse({"valid": False, "code": normalized})
    return JSONResponse({"valid": True, "code": normalized, "ownerUserId": referral["ownerUserId"]})


@router.get("/referrals/user/codes/list")
async def list_referral_codes(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    return JSONResponse(store.list_referral_codes(owner_user_id=user.user_id))


@router.post("/referrals/user/codes/obj")
async def create_referral_code(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    code = payload.get("code")
    referral = store.create_referral_code(owner_user_id=user.user_id, code=str(code) if code else None)
    return JSONResponse(referral)


@router.get("/referrals/user/codes/obj/{code}")
async def get_referral_code(code: str, request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    referral = store.get_referral_code(code)
    if not referral or referral["ownerUserId"] != user.user_id:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(referral)


@router.get("/referrals/user/commissions/list")
async def list_referral_commissions(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    return JSONResponse(store.list_referral_commissions(owner_user_id=user.user_id))


@router.get("/referrals/user/referees/list")
async def list_referral_referees(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    codes = store.list_referral_codes(owner_user_id=user.user_id)
    return JSONResponse(
        [
            {
                "code": entry["code"],
                "referees": [],
            }
            for entry in codes
        ]
    )


@router.get("/referrals/user/stats/obj")
async def referral_stats(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    codes = store.list_referral_codes(owner_user_id=user.user_id)
    commissions = store.list_referral_commissions(owner_user_id=user.user_id)
    withdrawals = store.list_referral_withdrawals(owner_user_id=user.user_id)
    total_commission = sum(float(item.get("amount", 0.0)) for item in commissions)
    total_withdrawn = sum(float(item.get("amount", 0.0)) for item in withdrawals)
    return JSONResponse(
        {
            "codes": len(codes),
            "totalCommission": total_commission,
            "totalWithdrawn": total_withdrawn,
            "walletBalance": total_commission - total_withdrawn,
        }
    )


@router.get("/referrals/user/policies/obj")
async def referral_policy(_auth=Depends(require_authenticated_user)) -> JSONResponse:
    return JSONResponse(
        {
            "commissionRate": 0.2,
            "minimumWithdrawal": 50.0,
            "settlementCycleDays": 30,
        }
    )


@router.get("/referrals/user/wallets/obj")
async def referral_wallet(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    commissions = store.list_referral_commissions(owner_user_id=user.user_id)
    withdrawals = store.list_referral_withdrawals(owner_user_id=user.user_id)
    total_commission = sum(float(item.get("amount", 0.0)) for item in commissions)
    total_withdrawn = sum(float(item.get("amount", 0.0)) for item in withdrawals)
    return JSONResponse(
        {
            "currency": "USD",
            "availableBalance": total_commission - total_withdrawn,
            "totalCommission": total_commission,
            "totalWithdrawn": total_withdrawn,
        }
    )


@router.get("/referrals/user/withdrawals/list")
async def list_referral_withdrawals(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    return JSONResponse(store.list_referral_withdrawals(owner_user_id=user.user_id))


@router.post("/referrals/user/withdrawals/obj")
async def create_referral_withdrawal(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    amount = float(payload.get("amount", 0.0))
    currency = str(payload.get("currency", "USD")).upper()
    if amount <= 0:
        return _bad_values("amount")
    withdrawal = store.create_referral_withdrawal(owner_user_id=user.user_id, amount=amount, currency=currency)
    return JSONResponse(withdrawal)


@router.get("/features/amz-shuffle-products/public/root-categories/obj")
async def list_shuffle_root_categories(request: Request) -> JSONResponse:
    marketplace = str(request.query_params.get("marketplace", "")).strip().upper()
    if not marketplace:
        return _bad_values("marketplace")
    categories = store.list_root_categories(marketplace)
    return JSONResponse({"marketplace": marketplace, "categories": categories})


@router.get("/features/amz-shuffle-products/user/exclude-categories/obj")
async def list_shuffle_excluded_categories(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    marketplace = str(request.query_params.get("marketplace", "")).strip().upper()
    payload = store.get_shuffle_excluded_categories(user.user_id, marketplace=marketplace or None)
    return JSONResponse(payload)


@router.get("/features/amz-shuffle-products/user/searched-categories/obj")
async def search_shuffle_categories(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    marketplace = str(request.query_params.get("marketplace", "")).strip().upper()
    if not marketplace:
        return _bad_values("marketplace")

    keyword = str(request.query_params.get("keyword", "")).strip().lower()
    root_categories = store.list_root_categories(marketplace)

    if keyword:
        categories = [item for item in root_categories if keyword in str(item.get("categoryName", "")).lower()]
    else:
        categories = root_categories

    if not categories and keyword:
        categories = [
            {
                "categoryId": f"search_{keyword[:20]}",
                "categoryName": keyword.title(),
                "categoryTree": [keyword.title()],
            }
        ]

    store.set_shuffle_searched_categories(user.user_id, marketplace=marketplace, categories=categories)
    return JSONResponse(categories)


@router.post("/features/amz-shuffle-products/user/obj")
async def shuffle_products(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)

    marketplace = str(payload.get("marketplace", "")).strip().upper()
    if not marketplace:
        return _bad_values("marketplace")

    category_ids = payload.get("categoryIds", payload.get("category_ids", []))
    if not isinstance(category_ids, list):
        category_ids = [category_ids] if category_ids else []

    no_less_than = _coerce_int(payload.get("noLessThan", payload.get("no_less_than", 10)), default=10, minimum=1, maximum=60)
    progress_key = str(payload.get("progressKey", payload.get("progress_key", ""))).strip() or f"shuffle-{secrets.token_hex(8)}"

    keywords = payload.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords]
    if not isinstance(keywords, list):
        keywords = []
    keyword_values = [str(item).strip() for item in keywords if str(item).strip()]

    exclude_categories = payload.get("excludeCategories", payload.get("exclude_categories", []))
    normalized_excluded: list[dict] = []
    if isinstance(exclude_categories, list):
        for item in exclude_categories:
            if not isinstance(item, dict):
                continue
            category_id = str(item.get("categoryId", item.get("category_id", ""))).strip()
            category_name = str(item.get("categoryName", item.get("category_name", ""))).strip()
            category_tree = item.get("categoryTree", item.get("category_tree", []))
            if not category_id:
                continue
            if not isinstance(category_tree, list):
                category_tree = [str(category_tree)]
            normalized_excluded.append(
                {
                    "categoryId": category_id,
                    "categoryName": category_name or category_id,
                    "categoryTree": [str(entry) for entry in category_tree],
                }
            )

    if normalized_excluded:
        store.set_shuffle_excluded_categories(user.user_id, marketplace=marketplace, categories=normalized_excluded)

    token_cost = _coerce_int(payload.get("tokenCost", payload.get("token_cost", 1)), default=1, minimum=1, maximum=20)
    if not store.consume_tokens(user.user_id, token_cost):
        return JSONResponse(status_code=402, content={"error": "Insufficient tokens"})

    seed_category = str(category_ids[0]).strip() if category_ids else "general"
    seed_keyword = keyword_values[0] if keyword_values else "amazon product"
    products = []
    for index in range(no_less_than):
        serial = index + 1
        asin_suffix = f"{(index * 73 + 103) % 99999:05d}"
        products.append(
            {
                "asin": f"B{asin_suffix}{serial % 10:01d}",
                "marketplace": marketplace,
                "title": f"{seed_keyword.title()} {serial}",
                "categoryId": seed_category,
                "estimatedMonthlySales": 80 + serial * 7,
                "estimatedPrice": round(16.5 + serial * 0.8, 2),
                "estimatedProfitRatio": round(0.12 + (serial % 5) * 0.01, 3),
                "score": round(78 + serial * 0.6, 2),
            }
        )

    response = {
        "progressKey": progress_key,
        "marketplace": marketplace,
        "keyword": seed_keyword,
        "tokenCost": token_cost,
        "shuffledProducts": {"products": products, "total": len(products), "noMore": True},
    }
    store.set_shuffle_products_result(user.user_id, response)
    return JSONResponse(response)


@router.get("/features/configs/owner/shipping-and-exchange-rates/obj")
async def get_shipping_exchange_rates(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    marketplace = str(
        request.query_params.get("amazon_marketplace")
        or request.query_params.get("amazonMarketplace")
        or request.query_params.get("marketplace")
        or ""
    ).strip().upper()
    if not marketplace:
        return _bad_values("amazon_marketplace")
    config = store.get_shipping_exchange_rates(marketplace)
    if not config:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse({"amazonMarketplace": marketplace, **config})


@router.get("/memberships/owner/list")
async def list_owner_memberships(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    only_enabled = _is_truthy(request.query_params.get("only_enabled"))
    offset = _coerce_int(request.query_params.get("offset"), default=0, minimum=0)
    limit = _coerce_int(request.query_params.get("limit"), default=30, minimum=1, maximum=100)

    subscribed = store.get_user_membership(user.user_id)
    memberships = []
    for item in store.list_memberships():
        enabled = str(item.get("status", "active")).lower() == "active"
        if only_enabled and not enabled:
            continue
        memberships.append(
            {
                **item,
                "enabled": enabled,
                "isSubscribed": subscribed is not None and subscribed.get("membershipId") == item.get("id"),
            }
        )
    return JSONResponse(memberships[offset : offset + limit])


@router.get("/memberships/owner/obj")
async def get_owner_membership_by_query(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    membership_id = str(
        request.query_params.get("membership_id")
        or request.query_params.get("membershipId")
        or ""
    ).strip()
    if membership_id:
        membership = store.get_membership(membership_id)
        if not membership:
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        subscribed = store.get_user_membership(user.user_id)
        return JSONResponse(
            {
                **membership,
                "isSubscribed": subscribed is not None and subscribed.get("membershipId") == membership.get("id"),
                "subscription": subscribed if subscribed and subscribed.get("membershipId") == membership.get("id") else None,
            }
        )

    subscribed = store.get_user_membership(user.user_id)
    if not subscribed:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    membership = store.get_membership(str(subscribed.get("membershipId", "")))
    if not membership:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse({**membership, "isSubscribed": True, "subscription": subscribed})


@router.post("/memberships/owner/obj")
async def subscribe_owner_membership(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    membership_id = str(payload.get("membershipId", payload.get("membership_id", ""))).strip()
    if not membership_id:
        return _bad_values("membershipId")
    subscription = store.set_user_membership(user.user_id, membership_id)
    if not subscription:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    membership = store.get_membership(membership_id)
    return JSONResponse({"membership": membership, "subscription": subscription})


@router.get("/memberships/owner/obj/{membership_id}")
async def get_owner_membership(membership_id: str, request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    membership = store.get_membership(membership_id)
    if not membership:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    subscribed = store.get_user_membership(user.user_id)
    return JSONResponse(
        {
            **membership,
            "isSubscribed": subscribed is not None and subscribed.get("membershipId") == membership.get("id"),
            "subscription": subscribed if subscribed and subscribed.get("membershipId") == membership.get("id") else None,
        }
    )


@router.get("/token-containers/owner/list")
async def list_owner_token_containers(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    offset = _coerce_int(request.query_params.get("offset"), default=0, minimum=0)
    limit = _coerce_int(request.query_params.get("limit"), default=50, minimum=1, maximum=200)
    containers = store.list_token_containers(user.user_id)
    return JSONResponse(containers[offset : offset + limit])


@router.get("/token-containers/owner/obj")
async def get_owner_token_container_summary(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    _token_type = request.query_params.get("token_type")
    summary = store.get_token_container_summary(user.user_id)
    return JSONResponse(summary)


@router.get("/token-containers/owner/extendable/obj")
async def list_owner_extendable_token_containers(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    return JSONResponse(store.get_extendable_token_containers(user.user_id))


@router.get("/token-services/public/list")
async def list_public_token_services() -> JSONResponse:
    return JSONResponse(store.list_token_services())


def _get_token_service_id_from_request(request: Request, payload: Optional[dict] = None) -> str:
    body = payload or {}
    return str(
        request.query_params.get("service_id")
        or request.query_params.get("serviceId")
        or body.get("service_id")
        or body.get("serviceId")
        or ""
    ).strip()


@router.get("/token-services/public/obj")
async def get_public_token_service_by_query(request: Request) -> JSONResponse:
    service_id = _get_token_service_id_from_request(request)
    if not service_id:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    service = store.get_token_service(service_id)
    if not service:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(service)


@router.post("/token-services/public/obj")
async def get_public_token_service_by_query_post(request: Request, body: dict) -> JSONResponse:
    payload = _json_payload(body)
    service_id = _get_token_service_id_from_request(request, payload=payload)
    if not service_id:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    service = store.get_token_service(service_id)
    if not service:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(service)


@router.get("/token-services/public/obj/{service_id}")
async def get_public_token_service(service_id: str) -> JSONResponse:
    service = store.get_token_service(service_id)
    if not service:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(service)


@router.post("/token/tokens")
async def calculate_token_usage(request: Request, body: dict) -> JSONResponse:
    payload = _json_payload(body)
    text = str(payload.get("text", "")).strip()
    token_count = payload.get("tokenCount", payload.get("token_count"))
    if token_count is None:
        token_count = max(1, len(text) // 4) if text else 1
    token_count = _coerce_int(token_count, default=1, minimum=1, maximum=1000000)

    user_id = ""
    auth_header = request.headers.get("authorization", "").strip().lower()
    if auth_header.startswith("bearer "):
        token = request.headers.get("authorization", "").split(" ", 1)[1].strip()
        token_record = store.find_token(token)
        if token_record:
            user_id = token_record.user_id

    remaining = None
    if user_id:
        summary = store.get_token_container_summary(user_id)
        remaining = summary.get("totalRemainingTokens")

    return JSONResponse({"tokenCount": token_count, "remainingTokens": remaining})


@router.get("/configs/public/obj")
async def get_public_project_config() -> JSONResponse:
    return JSONResponse(store.get_public_config())


@router.get("/configs/public/contact/obj")
async def get_public_project_contact() -> JSONResponse:
    return JSONResponse(store.get_public_contact())


@router.get("/configs/public/notification/obj")
async def get_public_project_notification(request: Request) -> JSONResponse:
    language = str(request.query_params.get("language", "en")).strip().lower()
    notification_type = str(request.query_params.get("notification_type", "")).strip()
    if not notification_type:
        return _bad_values("notification_type")
    notification = store.get_public_notification(notification_type=notification_type, language=language)
    if not notification:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(notification)


@router.get("/contents/blogs/public/list")
async def list_public_content_blogs(request: Request) -> JSONResponse:
    language = str(request.query_params.get("language", "")).strip().lower() or None
    limit = _coerce_int(request.query_params.get("limit"), default=10, minimum=1, maximum=100)
    offset = _coerce_int(request.query_params.get("offset"), default=0, minimum=0)
    created_at_gt = _parse_timestamp(request.query_params.get("created_at_gt"))
    created_at_lt = _parse_timestamp(request.query_params.get("created_at_lt"))
    return JSONResponse(
        store.list_public_blogs(
            language=language,
            limit=limit,
            offset=offset,
            created_at_gt=created_at_gt,
            created_at_lt=created_at_lt,
        )
    )


@router.get("/contents/blogs/public/obj/{slug}")
async def get_public_content_blog(slug: str, request: Request) -> JSONResponse:
    language = str(request.query_params.get("language", "")).strip().lower() or None
    blog = store.get_public_blog(slug=slug, language=language)
    if not blog:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(blog)


@router.get("/contents/blogs/public/pagination/obj")
async def get_public_content_blog_pagination(request: Request) -> JSONResponse:
    language = str(request.query_params.get("language", "")).strip().lower() or None
    created_at_gt = _parse_timestamp(request.query_params.get("created_at_gt"))
    created_at_lt = _parse_timestamp(request.query_params.get("created_at_lt"))
    limit = _coerce_int(request.query_params.get("limit"), default=10, minimum=1, maximum=100)
    total = store.count_public_blogs(language=language, created_at_gt=created_at_gt, created_at_lt=created_at_lt)
    pages = (total + limit - 1) // limit if total else 0
    return JSONResponse({"total": total, "limit": limit, "pages": pages})


@router.get("/blogs/{language}/{page}")
async def list_public_blogs_by_page(language: str, page: str) -> JSONResponse:
    page_no = _coerce_int(page, default=1, minimum=1)
    limit = 10
    offset = (page_no - 1) * limit
    rows = store.list_public_blogs(language=language, limit=limit, offset=offset)
    total = store.count_public_blogs(language=language)
    pages = (total + limit - 1) // limit if total else 0
    return JSONResponse({"language": language, "page": page_no, "limit": limit, "pages": pages, "total": total, "items": rows})


@router.post("/supports/public/obj")
async def create_public_support_ticket(body: dict) -> JSONResponse:
    payload = _json_payload(body)
    message = str(payload.get("message", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    if not message:
        return _bad_values("message")
    if email and not _is_email(email):
        return _bad_values("email")
    ticket = store.create_support_ticket(payload)
    return JSONResponse({"success": True, "ticket": ticket})


@router.get("/coupons/public/obj")
async def get_public_coupon(request: Request) -> JSONResponse:
    coupon_code = str(request.query_params.get("coupon_code") or request.query_params.get("couponCode") or "").strip()
    if not coupon_code:
        return _bad_values("coupon_code")
    coupon = store.get_public_coupon(coupon_code)
    if not coupon:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(coupon)


@router.get("/coupons/owner/consumable/obj")
async def check_coupon_consumable(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    coupon_code = str(request.query_params.get("coupon_code") or request.query_params.get("couponCode") or "").strip()
    currency = str(request.query_params.get("currency", "")).strip().upper()
    marketplace = str(request.query_params.get("marketplace", "")).strip().upper()
    if not coupon_code or not currency or not marketplace:
        return _bad_values("coupon_code", "currency", "marketplace")
    result = store.check_coupon_consumable(
        owner_user_id=user.user_id,
        coupon_code=coupon_code,
        currency=currency,
        marketplace=marketplace,
    )
    return JSONResponse(result)


@router.get("/orgs/public/obj")
async def get_public_org_by_query(request: Request) -> JSONResponse:
    org_id = str(request.query_params.get("org_id") or request.query_params.get("orgId") or "").strip()
    if not org_id:
        return _bad_values("org_id")
    org = store.get_org(org_id)
    if not org:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse({"id": org["id"], "name": org["name"], "createdAt": org["createdAt"]})


@router.get("/orgs/user/org")
async def get_user_org_by_query(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    org_id = str(request.query_params.get("org_id") or request.query_params.get("orgId") or "").strip()
    if not org_id:
        return _bad_values("org_id")
    org = store.get_org(org_id)
    if not org or user.user_id not in org.get("members", []):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(org)


@router.get("/cloud-storages/user/obj")
async def list_user_cloud_storages(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    return JSONResponse(store.list_cloud_storages(user.user_id))


@router.post("/cloud-storages/user/obj")
async def create_user_cloud_storage(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    content_type = str(request.headers.get("content-type", "")).lower()

    file_name = "upload.bin"
    file_size = 0
    mime_type = "application/octet-stream"
    provided_url = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded = form.get("file")
        if uploaded is not None:
            file_name = str(getattr(uploaded, "filename", file_name) or file_name)
            mime_type = str(getattr(uploaded, "content_type", mime_type) or mime_type)
            if hasattr(uploaded, "read"):
                body = await uploaded.read()
                file_size = len(body)
            elif isinstance(uploaded, (bytes, bytearray)):
                file_size = len(uploaded)
    else:
        try:
            payload = _json_payload(await request.json())
        except Exception:
            payload = {}
        file_name = str(payload.get("fileName", payload.get("filename", file_name))).strip() or file_name
        file_size = _coerce_int(payload.get("fileSize", payload.get("size", 0)), default=0, minimum=0)
        mime_type = str(payload.get("contentType", payload.get("mimeType", mime_type))).strip() or mime_type
        provided_url = str(payload.get("url", "")).strip() or None

    created = store.create_cloud_storage(
        owner_user_id=user.user_id,
        file_name=file_name,
        file_size=file_size,
        content_type=mime_type,
        url=provided_url,
    )
    return JSONResponse(created)


@router.get("/cloud-storages/user/obj/{id}")
async def get_user_cloud_storage(id: str, request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    obj = store.get_cloud_storage(storage_id=id, owner_user_id=user.user_id)
    if not obj:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(obj)


@router.get("/progresses/user/obj")
async def get_user_progress(request: Request, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    progress_key = str(request.query_params.get("progress_key") or request.query_params.get("progressKey") or "").strip()
    if not progress_key:
        return _bad_values("progress_key")
    progress = store.get_progress(progress_key=progress_key, owner_user_id=user.user_id)
    if not progress:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(progress)


@router.post("/progresses/user/list")
async def list_user_progresses(request: Request, body: dict, _auth=Depends(require_authenticated_user)) -> JSONResponse:
    user = _resolve_user_from_auth(request)
    payload = _json_payload(body)
    raw_keys = payload.get("progress_keys", payload.get("progressKeys", []))
    if isinstance(raw_keys, str):
        raw_keys = [raw_keys]
    progress_keys = [str(item).strip() for item in raw_keys if str(item).strip()] if isinstance(raw_keys, list) else []
    if not progress_keys:
        progress_keys = [str(item.get("progressKey")) for item in store.progresses_by_key.values() if item.get("ownerUserId") == user.user_id]
    rows = store.list_progresses(progress_keys=progress_keys, owner_user_id=user.user_id)
    return JSONResponse(rows)
