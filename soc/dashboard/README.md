# Rashomon dashboard

React + Vite front end for the Rashomon SOC. Two views share one app:

- **Landing page** (`/`): `src/App.jsx`, `src/SecurifyHero.tsx`, `src/components/*` (Tailwind CDN).
- **SOC console** (`/#console`): `src/console/`, plain CSS on design tokens, no Tailwind.

```bash
npm install
npm run dev          # http://localhost:3001 (port 3000 is taken by Juice Shop)
npm test             # Vitest: derived values (counts, MTTD/MTTR, filters, buckets)
npm run typecheck    # strict tsc over src/console
npm run build
```

The console reads only live data from the FastAPI backend on `http://localhost:8000` (override with
`VITE_API_URL`). There is no mock or sample data; if the backend is down, panels show an error with Retry.

**Capture control:** the top bar shows whether NFStream capture is running and has a Stop / Start button
(`POST /api/traffic/stop|start`). The backend still starts capture on launch (the lab scripts rely on that).
If capture watches the API's own port (8000), it records the dashboard's own polling, so either stop it or
set the monitored port on the Network Traffic page to the service you are defending (e.g. 22).

## Console layout

```
src/console/
  ConsoleApp.tsx        composition root: picks the data source, routes the 8 pages
  data/source.ts        SocDataSource interface (the only thing components depend on)
  data/api.ts           ApiSocDataSource: FastAPI endpoints -> view models
  data/derive.ts        pure derived values (tested in derive.test.ts)
  data/kpis.ts          KPI tiles + detection-source rows
  data/live.ts          SSE latency tracker (MTTD, decision latency)
  hooks/useSocData.ts   one hook for every read: loading skeleton, error + Retry, polling
  shell/ pages/ components/ styles/
```

## Swapping or updating the backend binding

Components never call `fetch`. Everything goes through `SocDataSource`, so a backend API change
is absorbed in **one file**, `src/console/data/api.ts`:

1. **Field renamed or reshaped:** edit the mapper for that record (`mapAlert`, `mapIncident`,
   `mapDecision`, or the inline mapping in `getTraffic` / `getFlows` / `getStatus`). The view
   models in `data/types.ts` stay the same, so no component changes.
2. **Endpoint moved:** change the path in the matching private loader (`alertsRaw`, `incidentsRaw`,
   `decisionsRaw`, `overview`, `health`, `system`, `policyRaw`) or action method (`respond`, `release`, …).
3. **List limits changed:** update `data/limits.ts` (the backend caps alerts/decisions at 500, incidents at 200).
4. **New data needed:** add a method to `SocDataSource`, implement it in `ApiSocDataSource`
   (TypeScript fails the typecheck until you do), then read it with `useSocData`.
5. **A completely different backend:** write a new class that `implements SocDataSource` and return it
   from `createSource()` in `ConsoleApp.tsx`.

Endpoints currently used: `/health`, `/system/status`, `/system/mode`, `/api/dashboard/overview`,
`/api/incidents`, `/api/incidents/{id}`, `/api/incidents/{id}/respond|release`, `/api/alerts`,
`/api/decisions`, `/api/audit/verify`, `/api/policy`, `/api/traffic/status|flows|port|start|stop|clear`,
and the SSE stream `/api/events/stream`.

## How the derived figures are computed

- **Severity:** incidents use `max_risk` against the policy tiers from `/api/policy`; each alert takes the
  tier of the decision persisted with it (same `incident_id` + `ts`). Alerts with no matching decision show "Unscored".
- **Critical alerts:** decisions in the last 24 h with `risk_score >= tiers.critical`.
- **MTTR:** per incident, first alert (`first_seen`) → first `executed`/`approved` decision; median.
- **MTTD / decision latency:** the backend stamps an alert and its decision with the same time and doesn't
  persist capture time, so both are measured live from the SSE stream (capture → alert, capture → decision,
  paired by source IP) for the current browser session. They read "—" until live detections arrive.
- **Risk tiers** come only from `/api/policy` (no client-side defaults).
- **Decision-latency targets** are optional: set `decision_latency_targets_ms` in `config/policies.yaml`
  (served by `/api/policy`). Without them the panel shows measured medians compared with each other.
- Backend timestamps come from SQLite without a timezone and are read as UTC (`parseUtc`).
