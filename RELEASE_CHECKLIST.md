# Release Checklist

## One-click validation

```bash
cd /Users/somalia/Documents/New\ project\ 2/reverse-keble/keble.backend
./scripts/smoke_regression.sh
```

## One-command release gate (recommended)

This runs smoke regression, rebuilds `keble-recovery-kit.tar.gz`, and refreshes `forensics/ARTIFACT_HASHES.txt`.

```bash
cd /Users/somalia/Documents/New\ project\ 2/reverse-keble
./release_gate.sh
```

## Preflight

- Ensure `.venv` exists and dependencies are installed:
  - `./scripts/dev_bootstrap.sh`
- Confirm manifest and priority routes are in sync:
  - `python3 -m py_compile app/routes/priority_routes.py app/services/inmemory.py`

## Expected result

- Script ends with `SMOKE PASS: all checks completed`.
- Script validates:
  - manifest route coverage against `app/route_manifest.json`
  - auth flow and token issuance
  - public configs/content/support routes
  - report/shuffle/membership/token/coupon/cloud/progress/org flows

## If validation fails

- Check API startup/runtime log:
  - `/tmp/keble_smoke_uvicorn.log`
- Re-run with a custom port if needed:
  - `PORT=18100 ./scripts/smoke_regression.sh`
- Rebuild route manifest and retry:
  - `python scripts/build_route_manifest.py`
  - `./scripts/smoke_regression.sh`
