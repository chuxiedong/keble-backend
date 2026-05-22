# keble.backend (recovered skeleton)

This is a recovery-oriented backend skeleton generated from public frontend
bundle endpoint evidence.

It is designed to help you restore service quickly:

- Exposes `/api/v2/*` route stubs based on recovered endpoint paths
- Keeps auth behavior shape (`401 Not authenticated`) for owner/user routes
- Returns consistent JSON placeholders so frontend integration can resume

## Quick start

```bash
cd /Users/somalia/Documents/New\ project\ 2/reverse-keble/keble.backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_route_manifest.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

or one-shot bootstrap:

```bash
cd /Users/somalia/Documents/New\ project\ 2/reverse-keble/keble.backend
./scripts/dev_bootstrap.sh
./scripts/run_dev.sh
```

## Endpoints

- Health: `GET /healthz`
- API root: `GET /api/v2`
- Generated routes: `GET /api/v2/_meta/routes`
- Route count summary: `GET /api/v2/_meta/summary`

## Regression validation

Run one command to validate route coverage + critical flows end to end:

```bash
cd /Users/somalia/Documents/New\ project\ 2/reverse-keble/keble.backend
./scripts/smoke_regression.sh
```

Detailed release checks:

- `RELEASE_CHECKLIST.md`

One-command full release gate from project root:

```bash
cd /Users/somalia/Documents/New\ project\ 2/reverse-keble
./release_gate.sh
```

## Implemented priority routes

These routes are already upgraded from generic stubs to usable recovery logic:

- `POST /api/v2/users/public/email-code`
- `POST /api/v2/users/public/obj`
- `POST /api/v2/users/public/obj/login`
- `POST /api/v2/users/public/access-token/exchange`
- `POST /api/v2/users/public/obj/reset-password`
- `GET /api/v2/users/public/wechat/qrcode`
- `GET /api/v2/users/user/obj`
- `POST /api/v2/users/user/access-token/exchange-new`
- `POST /api/v2/users/user/wechat/detach`
- `GET /api/v2/users/user/wechat/qrcode/scan`
- `POST /api/v2/orders/user/stripe/checkout`
- `GET /api/v2/orders/owner/list`
- `POST /api/v2/orders/owner/obj`
- `GET /api/v2/orders/owner/obj/{order_id}`
- `POST /api/v2/orders/owner/obj/{order_id}/paid`
- `POST /api/v2/orders/owner/alipay/obj`
- `GET /api/v2/orders/owner/alipay/obj/{order_id}`
- `GET /api/v2/features/amz-product-reports/public/product-reports/show-case/list`
- `POST /api/v2/features/amz-product-reports/owner/tasks/obj`
- `GET /api/v2/features/amz-product-reports/owner/tasks/list`
- `GET /api/v2/features/amz-product-reports/owner/tasks/obj/{task_id}`
- `GET /api/v2/features/amz-product-reports/optional-owner/tasks/obj/{task_id}`
- `GET /api/v2/features/amz-product-reports/optional-owner/tasks/obj/{task_id}/report`
- `GET /api/v2/orgs/user/list`
- `POST /api/v2/orgs/user/org/obj`
- `GET /api/v2/orgs/user/org/{org_id}`
- `GET /api/v2/orgs/user/org/{org_id}/list`
- `GET /api/v2/orgs/public/obj/{org_id}`
- `POST /api/v2/orgs/user/org/{org_id}/add-admin`
- `POST /api/v2/orgs/user/org/{org_id}/add-superadmin`
- `POST /api/v2/orgs/user/org/{org_id}/invite`
- `POST /api/v2/orgs/user/org/{org_id}/remove`
- `POST /api/v2/orgs/user/org/{org_id}/leave`
- `GET /api/v2/referrals/public/validate-code`
- `GET /api/v2/referrals/user/codes/list`
- `POST /api/v2/referrals/user/codes/obj`
- `GET /api/v2/referrals/user/codes/obj/{code}`
- `GET /api/v2/referrals/user/commissions/list`
- `GET /api/v2/referrals/user/referees/list`
- `GET /api/v2/referrals/user/stats/obj`
- `GET /api/v2/referrals/user/policies/obj`
- `GET /api/v2/referrals/user/wallets/obj`
- `GET /api/v2/referrals/user/withdrawals/list`
- `POST /api/v2/referrals/user/withdrawals/obj`
- `GET /api/v2/features/amz-shuffle-products/public/root-categories/obj`
- `GET /api/v2/features/amz-shuffle-products/user/exclude-categories/obj`
- `GET /api/v2/features/amz-shuffle-products/user/searched-categories/obj`
- `POST /api/v2/features/amz-shuffle-products/user/obj`
- `GET /api/v2/features/configs/owner/shipping-and-exchange-rates/obj`
- `GET /api/v2/memberships/owner/list`
- `GET /api/v2/memberships/owner/obj`
- `POST /api/v2/memberships/owner/obj`
- `GET /api/v2/memberships/owner/obj/{membership_id}`
- `GET /api/v2/token-containers/owner/list`
- `GET /api/v2/token-containers/owner/obj`
- `GET /api/v2/token-containers/owner/extendable/obj`
- `GET /api/v2/token-services/public/list`
- `GET /api/v2/token-services/public/obj`
- `POST /api/v2/token-services/public/obj`
- `GET /api/v2/token-services/public/obj/{service_id}`
- `POST /api/v2/token/tokens`
- `GET /api/v2/configs/public/obj`
- `GET /api/v2/configs/public/contact/obj`
- `GET /api/v2/configs/public/notification/obj`
- `GET /api/v2/contents/blogs/public/list`
- `GET /api/v2/contents/blogs/public/obj/{slug}`
- `GET /api/v2/contents/blogs/public/pagination/obj`
- `GET /api/v2/blogs/{language}/{page}`
- `POST /api/v2/supports/public/obj`
- `GET /api/v2/coupons/public/obj`
- `GET /api/v2/coupons/owner/consumable/obj`
- `GET /api/v2/cloud-storages/user/obj`
- `POST /api/v2/cloud-storages/user/obj`
- `GET /api/v2/cloud-storages/user/obj/{id}`
- `GET /api/v2/progresses/user/obj`
- `POST /api/v2/progresses/user/list`
- `GET /api/v2/orgs/public/obj`
- `GET /api/v2/orgs/user/org`

As of the latest recovery sprint, all manifest routes in
`app/route_manifest.json` are implemented in the priority recovery router
(`keble.backend/recovery_coverage.md`).

## Notes

- Source manifests come from:
  - `../forensics/v2-endpoints.json`
  - `../forensics/v2-crawl-endpoints.txt`
- The generated manifest is written to `app/route_manifest.json`.
- This project is intentionally scaffold-first: add real business logic module
  by module while preserving the recovered route contract.
