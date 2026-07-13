# Public-safe scenario pack

The `scenarios` directory contains the three redacted fixtures used by the portfolio release proof:

- Conditional Access device-compliance block;
- missing resource assignment;
- guest/B2B tenant restriction.

They contain no real tenant IDs, user identities, credentials, domains, or production evidence.

Generate reports from these fixtures with:

```bash
cd backend
python scripts/build_release_pack.py --scenarios ../examples/scenarios --output ../release-proof
```

Generated reports are intentionally not committed. GitHub Actions rebuilds them from the tagged source, records SHA-256 digests in `manifest.json`, and publishes them in the downloadable release-proof artifacts.
