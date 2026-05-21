from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class UserRecord:
    user_id: str
    email: str
    password: str
    nickname: str
    created_at: int


@dataclass
class TokenRecord:
    token: str
    user_id: str
    issued_at: int
    expires_in: int
    refresh_token: str


class RecoveryStore:
    def __init__(self) -> None:
        now = int(time.time())
        self.users_by_id: Dict[str, UserRecord] = {}
        self.users_by_email: Dict[str, UserRecord] = {}
        self.tokens: Dict[str, TokenRecord] = {}
        self.email_codes: Dict[str, dict] = {}
        self.orders: List[dict] = []
        self.report_tasks: Dict[str, dict] = {}
        self.orgs: Dict[str, dict] = {}
        self.referral_codes: List[dict] = []
        self.referral_commissions: List[dict] = []
        self.referral_withdrawals: List[dict] = []
        self.token_services: List[dict] = [
            {"id": "svc_amz_report_basic", "name": "AMZ Report Basic", "tokens": 10, "price": 19.0, "currency": "USD"},
            {"id": "svc_amz_report_pro", "name": "AMZ Report Pro", "tokens": 35, "price": 59.0, "currency": "USD"},
            {"id": "svc_shuffle_pack", "name": "Shuffle Product Pack", "tokens": 25, "price": 29.0, "currency": "USD"},
        ]
        self.memberships: List[dict] = [
            {"id": "membership_starter", "name": "Starter", "monthlyPrice": 19.0, "currency": "USD", "status": "active"},
            {"id": "membership_growth", "name": "Growth", "monthlyPrice": 49.0, "currency": "USD", "status": "active"},
            {"id": "membership_pro", "name": "Pro", "monthlyPrice": 99.0, "currency": "USD", "status": "active"},
        ]
        self.membership_by_user: Dict[str, dict] = {}
        self.token_containers_by_user: Dict[str, List[dict]] = {}
        self.shuffle_excluded_categories_by_user: Dict[str, Dict[str, List[dict]]] = {}
        self.shuffle_searched_categories_by_user: Dict[str, Dict[str, List[dict]]] = {}
        self.shuffle_products_by_user: Dict[str, dict] = {}
        self.shuffle_root_categories_by_marketplace: Dict[str, List[dict]] = {
            "US": [
                {"categoryId": "home-kitchen", "categoryName": "Home & Kitchen", "categoryTree": ["Home & Kitchen"]},
                {"categoryId": "pet-supplies", "categoryName": "Pet Supplies", "categoryTree": ["Pet Supplies"]},
                {"categoryId": "sports-outdoors", "categoryName": "Sports & Outdoors", "categoryTree": ["Sports & Outdoors"]},
            ],
            "DE": [
                {"categoryId": "haus-kueche", "categoryName": "Haushalt & Küche", "categoryTree": ["Haushalt", "Küche"]},
                {"categoryId": "haustierbedarf", "categoryName": "Haustierbedarf", "categoryTree": ["Haustierbedarf"]},
            ],
            "UK": [
                {"categoryId": "home-garden", "categoryName": "Home & Garden", "categoryTree": ["Home & Garden"]},
                {"categoryId": "beauty", "categoryName": "Beauty", "categoryTree": ["Beauty"]},
            ],
        }
        self.shipping_exchange_rates_by_marketplace: Dict[str, dict] = {
            "US": {"currency": "USD", "exchangeRateToUSD": 1.0, "shippingProfile": {"name": "US Standard", "fbaBase": 4.5}},
            "DE": {"currency": "EUR", "exchangeRateToUSD": 1.08, "shippingProfile": {"name": "DE Standard", "fbaBase": 4.2}},
            "UK": {"currency": "GBP", "exchangeRateToUSD": 1.26, "shippingProfile": {"name": "UK Standard", "fbaBase": 4.0}},
        }
        self.report_showcases: List[dict] = [
            {
                "id": "showcase-demo-1",
                "marketplace": "US",
                "asin": "B08N5L5R6P",
                "title": "Portable Blender Bottle",
                "createdAt": now,
            }
        ]
        self.public_project_config: dict = {
            "projectName": "Keble 2.0",
            "assistantName": "Listing 2.0",
            "language": "ENGLISH",
            "supportEmail": "support@keble.ai",
            "maxFileSizeInMb": 30,
            "monthlyFreeToken": 200000,
            "featureTokenCosts": {
                "SALES_PREDICTION": 10,
                "REVIEW_ANALYSIS": 12,
                "PRODUCT_ANALYSIS": 14,
            },
        }
        self.public_contact_config: dict = {
            "email": "support@keble.ai",
            "qrcode": {
                "id": 1,
                "label": "Keble Support",
                "url": "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=keble-recovery-ticket",
            },
        }
        self.public_notifications: List[dict] = [
            {
                "id": "notice_maintenance_en",
                "language": "en",
                "notificationType": "MAINTENANCE",
                "label": "Maintenance Notice",
                "description": "Service window on Sunday 02:00-03:00 UTC.",
                "url": "https://keble.ai/status",
                "forceAlertDialog": False,
            },
            {
                "id": "notice_maintenance_zh",
                "language": "zh",
                "notificationType": "MAINTENANCE",
                "label": "维护通知",
                "description": "服务将在周日 UTC 02:00-03:00 维护。",
                "url": "https://keble.ai/status",
                "forceAlertDialog": False,
            },
        ]
        self.public_blogs: List[dict] = [
            {
                "id": "blog_en_1",
                "slug": "how-ai-helps-amazon-research",
                "language": "en",
                "title": "How AI helps Amazon product research",
                "description": "A practical workflow for faster niche validation.",
                "keywords": ["amazon", "ai", "research"],
                "createdAt": now - 86400 * 5,
                "content": "Use AI to narrow categories, score products, and test risk quickly.",
            },
            {
                "id": "blog_en_2",
                "slug": "pricing-with-confidence",
                "language": "en",
                "title": "Pricing with confidence in volatile markets",
                "description": "A margin-first approach to avoid underpricing.",
                "keywords": ["pricing", "margin", "amazon"],
                "createdAt": now - 86400 * 18,
                "content": "Start from target margin and back-calculate viable price windows.",
            },
            {
                "id": "blog_zh_1",
                "slug": "ai-ya-ma-xun-xuan-pin-shi-zhan",
                "language": "zh",
                "title": "AI 亚马逊选品实战",
                "description": "如何用 AI 快速评估市场机会。",
                "keywords": ["亚马逊", "选品", "AI"],
                "createdAt": now - 86400 * 8,
                "content": "先筛大类，再看利润率，再看竞争格局，最后决定切入策略。",
            },
        ]
        self.cloud_storages_by_id: Dict[str, dict] = {}
        self.progresses_by_key: Dict[str, dict] = {}
        self.support_tickets: List[dict] = []
        self.public_coupons: List[dict] = [
            {
                "couponCode": "WELCOME10",
                "discountType": "PERCENTAGE",
                "discountValue": 10,
                "currency": "USD",
                "marketplace": "US",
                "enabled": True,
                "expiresAt": now + 86400 * 180,
            },
            {
                "couponCode": "CN88",
                "discountType": "FIXED",
                "discountValue": 88,
                "currency": "CNY",
                "marketplace": "CN",
                "enabled": True,
                "expiresAt": now + 86400 * 180,
            },
        ]

    def _ensure_user(self, email: str, password: str = "password123") -> UserRecord:
        key = email.strip().lower()
        existing = self.users_by_email.get(key)
        if existing:
            return existing

        user = UserRecord(
            user_id=str(uuid4()),
            email=key,
            password=password,
            nickname=key.split("@", 1)[0] or "user",
            created_at=int(time.time()),
        )
        self.users_by_id[user.user_id] = user
        self.users_by_email[user.email] = user
        return user

    def create_or_update_user(self, email: str, password: str) -> UserRecord:
        key = email.strip().lower()
        user = self._ensure_user(key, password=password)
        user.password = password
        self._ensure_user_token_containers(user.user_id)
        return user

    def find_user_by_email(self, email: str) -> Optional[UserRecord]:
        return self.users_by_email.get(email.strip().lower())

    def find_user_by_id(self, user_id: str) -> Optional[UserRecord]:
        return self.users_by_id.get(user_id)

    def _ensure_user_token_containers(self, user_id: str) -> List[dict]:
        containers = self.token_containers_by_user.get(user_id)
        if containers is not None:
            return containers
        containers = [
            {
                "id": f"container_main_{user_id[:8]}",
                "ownerUserId": user_id,
                "name": "Main Container",
                "remainingTokens": 100,
                "totalTokens": 100,
                "extendable": True,
                "updatedAt": int(time.time()),
            }
        ]
        self.token_containers_by_user[user_id] = containers
        return containers

    def issue_token(self, user_id: str, expires_in: int = 7200) -> TokenRecord:
        token = "keble_" + secrets.token_urlsafe(24)
        refresh_token = "keble_r_" + secrets.token_urlsafe(20)
        record = TokenRecord(
            token=token,
            user_id=user_id,
            issued_at=int(time.time()),
            expires_in=expires_in,
            refresh_token=refresh_token,
        )
        self.tokens[token] = record
        return record

    def find_token(self, token: str) -> Optional[TokenRecord]:
        return self.tokens.get(token)

    def save_email_code(self, email: str, purpose: str, code: str, ttl: int = 600) -> None:
        self.email_codes[f"{email.strip().lower()}::{purpose.strip().lower()}"] = {
            "email": email.strip().lower(),
            "purpose": purpose.strip().lower(),
            "code": code,
            "expires_at": int(time.time()) + ttl,
        }

    def verify_email_code(self, email: str, purpose: str, code: str) -> bool:
        key = f"{email.strip().lower()}::{purpose.strip().lower()}"
        record = self.email_codes.get(key)
        if not record:
            return False
        if int(time.time()) > int(record["expires_at"]):
            return False
        return str(record["code"]) == str(code)

    def add_order(self, payload: dict) -> dict:
        order = {"id": str(uuid4()), "createdAt": int(time.time()), **payload}
        self.orders.append(order)
        return order

    def list_orders(self) -> List[dict]:
        return list(self.orders)

    def get_order(self, order_id: str) -> Optional[dict]:
        for order in self.orders:
            if order.get("id") == order_id:
                return order
        return None

    def mark_order_paid(self, order_id: str) -> Optional[dict]:
        order = self.get_order(order_id)
        if order is None:
            return None
        order["status"] = "paid"
        order["paidAt"] = int(time.time())
        return order

    def add_report_task(self, owner_user_id: str, asin: str, marketplace: str, keyword: str) -> dict:
        task_id = str(uuid4())
        now = int(time.time())
        task = {
            "taskId": task_id,
            "ownerUserId": owner_user_id,
            "asin": asin,
            "marketplace": marketplace,
            "keyword": keyword,
            "status": "completed",
            "createdAt": now,
            "reportId": f"report_{task_id}",
        }
        self.report_tasks[task_id] = task
        self.set_progress(
            owner_user_id=owner_user_id,
            progress_key=f"report:{task_id}",
            status="SUCCESS",
            percent=100,
            message="Report task completed",
            meta={"taskId": task_id, "reportId": task["reportId"]},
        )
        return task

    def get_report_task(self, task_id: str) -> Optional[dict]:
        return self.report_tasks.get(task_id)

    def list_report_tasks(self, owner_user_id: str) -> List[dict]:
        return [task for task in self.report_tasks.values() if task["ownerUserId"] == owner_user_id]

    def list_memberships(self) -> List[dict]:
        return list(self.memberships)

    def get_membership(self, membership_id: str) -> Optional[dict]:
        for item in self.memberships:
            if item.get("id") == membership_id:
                return item
        return None

    def get_user_membership(self, user_id: str) -> Optional[dict]:
        return self.membership_by_user.get(user_id)

    def set_user_membership(self, user_id: str, membership_id: str) -> Optional[dict]:
        membership = self.get_membership(membership_id)
        if membership is None:
            return None
        now = int(time.time())
        subscription = {
            "id": f"sub_{user_id[:8]}_{membership_id}",
            "ownerUserId": user_id,
            "membershipId": membership["id"],
            "membershipName": membership["name"],
            "status": "active",
            "startedAt": now,
            "renewalAt": now + 30 * 24 * 3600,
        }
        self.membership_by_user[user_id] = subscription
        return subscription

    def list_token_services(self) -> List[dict]:
        return list(self.token_services)

    def get_token_service(self, service_id: str) -> Optional[dict]:
        for item in self.token_services:
            if item.get("id") == service_id:
                return item
        return None

    def list_token_containers(self, user_id: str) -> List[dict]:
        return list(self._ensure_user_token_containers(user_id))

    def get_extendable_token_containers(self, user_id: str) -> List[dict]:
        return [c for c in self._ensure_user_token_containers(user_id) if c.get("extendable")]

    def get_token_container_summary(self, user_id: str) -> dict:
        containers = self._ensure_user_token_containers(user_id)
        total_remaining = sum(int(item.get("remainingTokens", 0)) for item in containers)
        return {"ownerUserId": user_id, "totalRemainingTokens": total_remaining, "containers": containers}

    def consume_tokens(self, user_id: str, amount: int) -> bool:
        containers = self._ensure_user_token_containers(user_id)
        if amount <= 0:
            return True
        total_remaining = sum(int(item.get("remainingTokens", 0)) for item in containers)
        if total_remaining < amount:
            return False
        left = amount
        for container in containers:
            cur = int(container.get("remainingTokens", 0))
            if cur <= 0:
                continue
            cut = min(cur, left)
            container["remainingTokens"] = cur - cut
            container["updatedAt"] = int(time.time())
            left -= cut
            if left <= 0:
                break
        return True

    def get_shipping_exchange_rates(self, marketplace: str) -> Optional[dict]:
        return self.shipping_exchange_rates_by_marketplace.get(marketplace.upper())

    def list_root_categories(self, marketplace: str) -> List[dict]:
        return list(self.shuffle_root_categories_by_marketplace.get(marketplace.upper(), []))

    def get_shuffle_excluded_categories(self, user_id: str, marketplace: Optional[str] = None) -> List[dict]:
        by_marketplace = self.shuffle_excluded_categories_by_user.get(user_id, {})
        if marketplace:
            target = marketplace.upper()
            categories = list(by_marketplace.get(target, []))
            if not categories:
                return []
            return [{"marketplace": target, "excludeCategories": categories}]
        payload: List[dict] = []
        for key, categories in by_marketplace.items():
            payload.append({"marketplace": key, "excludeCategories": list(categories)})
        return payload

    def set_shuffle_excluded_categories(self, user_id: str, marketplace: str, categories: List[dict]) -> List[dict]:
        target = marketplace.upper()
        by_marketplace = self.shuffle_excluded_categories_by_user.setdefault(user_id, {})
        by_marketplace[target] = list(categories)
        return self.get_shuffle_excluded_categories(user_id, marketplace=target)

    def get_shuffle_searched_categories(self, user_id: str, marketplace: Optional[str] = None) -> List[dict]:
        by_marketplace = self.shuffle_searched_categories_by_user.get(user_id, {})
        if marketplace:
            return list(by_marketplace.get(marketplace.upper(), []))
        merged: List[dict] = []
        for categories in by_marketplace.values():
            merged.extend(categories)
        return merged

    def set_shuffle_searched_categories(self, user_id: str, marketplace: str, categories: List[dict]) -> List[dict]:
        target = marketplace.upper()
        by_marketplace = self.shuffle_searched_categories_by_user.setdefault(user_id, {})
        by_marketplace[target] = list(categories)
        return self.get_shuffle_searched_categories(user_id, marketplace=target)

    def set_shuffle_products_result(self, user_id: str, payload: dict) -> dict:
        self.shuffle_products_by_user[user_id] = payload
        return payload

    def get_shuffle_products_result(self, user_id: str) -> Optional[dict]:
        return self.shuffle_products_by_user.get(user_id)

    def get_public_config(self) -> dict:
        return dict(self.public_project_config)

    def get_public_contact(self) -> dict:
        return dict(self.public_contact_config)

    def get_public_notification(self, notification_type: str, language: str) -> Optional[dict]:
        target_type = notification_type.strip().upper()
        target_language = language.strip().lower()
        for entry in self.public_notifications:
            if (
                str(entry.get("notificationType", "")).upper() == target_type
                and str(entry.get("language", "")).lower() == target_language
            ):
                return dict(entry)
        return None

    def list_public_blogs(
        self,
        language: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        created_at_gt: Optional[int] = None,
        created_at_lt: Optional[int] = None,
    ) -> List[dict]:
        rows = list(self.public_blogs)
        if language:
            target = language.strip().lower()
            rows = [item for item in rows if str(item.get("language", "")).lower() == target]
        if created_at_gt is not None:
            rows = [item for item in rows if int(item.get("createdAt", 0)) > int(created_at_gt)]
        if created_at_lt is not None:
            rows = [item for item in rows if int(item.get("createdAt", 0)) < int(created_at_lt)]
        rows.sort(key=lambda item: int(item.get("createdAt", 0)), reverse=True)
        return [dict(item) for item in rows[offset : offset + limit]]

    def get_public_blog(self, slug: str, language: Optional[str] = None) -> Optional[dict]:
        target_slug = slug.strip()
        target_language = language.strip().lower() if language else ""
        for item in self.public_blogs:
            if str(item.get("slug", "")) != target_slug:
                continue
            if target_language and str(item.get("language", "")).lower() != target_language:
                continue
            return dict(item)
        return None

    def count_public_blogs(
        self,
        language: Optional[str] = None,
        created_at_gt: Optional[int] = None,
        created_at_lt: Optional[int] = None,
    ) -> int:
        return len(
            self.list_public_blogs(
                language=language,
                limit=100000,
                offset=0,
                created_at_gt=created_at_gt,
                created_at_lt=created_at_lt,
            )
        )

    def create_cloud_storage(
        self,
        owner_user_id: str,
        file_name: str,
        file_size: int = 0,
        content_type: str = "application/octet-stream",
        url: Optional[str] = None,
    ) -> dict:
        storage_id = str(uuid4())
        payload = {
            "id": storage_id,
            "ownerUserId": owner_user_id,
            "fileName": file_name,
            "fileSize": max(0, int(file_size)),
            "contentType": content_type,
            "url": url or f"https://storage.keble.local/{storage_id}/{file_name}",
            "createdAt": int(time.time()),
        }
        self.cloud_storages_by_id[storage_id] = payload
        return dict(payload)

    def get_cloud_storage(self, storage_id: str, owner_user_id: Optional[str] = None) -> Optional[dict]:
        payload = self.cloud_storages_by_id.get(storage_id)
        if payload is None:
            return None
        if owner_user_id and payload.get("ownerUserId") != owner_user_id:
            return None
        return dict(payload)

    def list_cloud_storages(self, owner_user_id: str) -> List[dict]:
        rows = [dict(item) for item in self.cloud_storages_by_id.values() if item.get("ownerUserId") == owner_user_id]
        rows.sort(key=lambda item: int(item.get("createdAt", 0)), reverse=True)
        return rows

    def set_progress(
        self,
        owner_user_id: str,
        progress_key: str,
        status: str,
        percent: int,
        message: str,
        meta: Optional[dict] = None,
    ) -> dict:
        now = int(time.time())
        payload = {
            "progressKey": progress_key,
            "ownerUserId": owner_user_id,
            "status": status,
            "percent": max(0, min(100, int(percent))),
            "message": message,
            "updatedAt": now,
            "meta": meta or {},
        }
        if progress_key not in self.progresses_by_key:
            payload["createdAt"] = now
        else:
            payload["createdAt"] = int(self.progresses_by_key[progress_key].get("createdAt", now))
        self.progresses_by_key[progress_key] = payload
        return dict(payload)

    def get_progress(self, progress_key: str, owner_user_id: Optional[str] = None) -> Optional[dict]:
        payload = self.progresses_by_key.get(progress_key)
        if payload is None:
            return None
        if owner_user_id and payload.get("ownerUserId") != owner_user_id:
            return None
        return dict(payload)

    def list_progresses(self, progress_keys: List[str], owner_user_id: Optional[str] = None) -> List[dict]:
        rows: List[dict] = []
        for key in progress_keys:
            item = self.get_progress(key, owner_user_id=owner_user_id)
            if item is not None:
                rows.append(item)
        return rows

    def create_support_ticket(self, payload: dict) -> dict:
        now = int(time.time())
        ticket = {
            "id": str(uuid4()),
            "name": str(payload.get("name", "")).strip(),
            "email": str(payload.get("email", "")).strip().lower(),
            "message": str(payload.get("message", "")).strip(),
            "source": str(payload.get("source", "public")).strip(),
            "status": "received",
            "createdAt": now,
        }
        self.support_tickets.append(ticket)
        return dict(ticket)

    def get_public_coupon(self, coupon_code: str) -> Optional[dict]:
        target = coupon_code.strip().upper()
        for item in self.public_coupons:
            if str(item.get("couponCode", "")).upper() == target:
                return dict(item)
        return None

    def check_coupon_consumable(
        self,
        owner_user_id: str,
        coupon_code: str,
        currency: str,
        marketplace: str,
    ) -> dict:
        coupon = self.get_public_coupon(coupon_code)
        now = int(time.time())
        if coupon is None:
            return {"consumable": False, "reason": "coupon_not_found"}
        if not bool(coupon.get("enabled", False)):
            return {"consumable": False, "reason": "coupon_disabled", "coupon": coupon}
        if int(coupon.get("expiresAt", 0)) < now:
            return {"consumable": False, "reason": "coupon_expired", "coupon": coupon}
        coupon_currency = str(coupon.get("currency", "")).upper()
        coupon_marketplace = str(coupon.get("marketplace", "")).upper()
        if coupon_currency and coupon_currency != currency.strip().upper():
            return {"consumable": False, "reason": "currency_mismatch", "coupon": coupon}
        if coupon_marketplace and coupon_marketplace != marketplace.strip().upper():
            return {"consumable": False, "reason": "marketplace_mismatch", "coupon": coupon}
        return {"consumable": True, "reason": "ok", "coupon": coupon, "ownerUserId": owner_user_id}

    def create_org(self, owner_user_id: str, name: str) -> dict:
        now = int(time.time())
        org_id = str(uuid4())
        org = {
            "id": org_id,
            "name": name,
            "ownerUserId": owner_user_id,
            "admins": [owner_user_id],
            "members": [owner_user_id],
            "invites": [],
            "createdAt": now,
        }
        self.orgs[org_id] = org
        return org

    def get_org(self, org_id: str) -> Optional[dict]:
        return self.orgs.get(org_id)

    def list_orgs_by_user(self, user_id: str) -> List[dict]:
        result = []
        for org in self.orgs.values():
            if user_id in org.get("members", []):
                result.append(org)
        return result

    def add_org_member(self, org_id: str, user_id: str, as_admin: bool = False) -> Optional[dict]:
        org = self.get_org(org_id)
        if org is None:
            return None
        if user_id not in org["members"]:
            org["members"].append(user_id)
        if as_admin and user_id not in org["admins"]:
            org["admins"].append(user_id)
        return org

    def remove_org_member(self, org_id: str, user_id: str) -> Optional[dict]:
        org = self.get_org(org_id)
        if org is None:
            return None
        org["members"] = [member for member in org["members"] if member != user_id]
        org["admins"] = [admin for admin in org["admins"] if admin != user_id]
        return org

    def create_referral_code(self, owner_user_id: str, code: Optional[str] = None) -> dict:
        normalized = code.strip().upper() if code else ("KBL" + secrets.token_hex(3).upper())
        now = int(time.time())
        existing = self.get_referral_code(normalized)
        if existing:
            return existing
        record = {
            "code": normalized,
            "ownerUserId": owner_user_id,
            "createdAt": now,
            "status": "active",
            "uses": 0,
        }
        self.referral_codes.append(record)
        return record

    def get_referral_code(self, code: str) -> Optional[dict]:
        target = code.strip().upper()
        for record in self.referral_codes:
            if record.get("code") == target:
                return record
        return None

    def list_referral_codes(self, owner_user_id: str) -> List[dict]:
        return [record for record in self.referral_codes if record.get("ownerUserId") == owner_user_id]

    def list_referral_commissions(self, owner_user_id: str) -> List[dict]:
        return [item for item in self.referral_commissions if item.get("ownerUserId") == owner_user_id]

    def list_referral_withdrawals(self, owner_user_id: str) -> List[dict]:
        return [item for item in self.referral_withdrawals if item.get("ownerUserId") == owner_user_id]

    def create_referral_withdrawal(self, owner_user_id: str, amount: float, currency: str) -> dict:
        now = int(time.time())
        payload = {
            "id": str(uuid4()),
            "ownerUserId": owner_user_id,
            "amount": amount,
            "currency": currency.upper(),
            "status": "pending",
            "createdAt": now,
        }
        self.referral_withdrawals.append(payload)
        return payload


store = RecoveryStore()
