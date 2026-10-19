/** Backend caps on list endpoints: /api/alerts and /api/decisions ≤ 500, /api/incidents ≤ 200. */
export const FETCH_LIMITS = { alerts: 500, decisions: 500, incidents: 200 } as const;
