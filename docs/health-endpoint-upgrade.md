## Health Endpoint Upgrade Guide

### Summary of Changes

- `/health` now returns structured check entries where each key maps to an object containing a `status` field (and optional `detail`) instead of raw strings.
- `service_info` replaces the previous flat `service`, `version`, and `timestamp` keys.
- Status values are standardized to `healthy`, `unhealthy`, `error`, or `informational` to simplify filtering on the client.

### Client Action Items

1. **Update response parsing**
   - Expect each entry in `checks` to be a dictionary: `checks.database.status` rather than a bare string.
   - Prefer truthy comparisons such as `checks.database.status === "healthy"`.

2. **Handle details**
   - When `status` is `unhealthy` or `error`, read `detail` for an operator-friendly message; render it in admin dashboards.

3. **Service metadata**
   - Read `checks.service_info` for name/version/timestamp instead of the previously separate keys.

4. **Alerting / monitoring**
   - Update any health probes to treat `status !== "healthy"` as a failure and optionally surface the `detail` string.

### Verification Checklist

- [ ] Client deserializes the new `checks` object shape.
- [ ] UI badges switch to `checks.service_info.name` and `.version`.
- [ ] Alerts capture `detail` when `status` ≠ `healthy`.
