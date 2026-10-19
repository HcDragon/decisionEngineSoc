import type { PipelineEvent, Severity } from './types';
import { median, normalizeTier } from './derive';

/**
 * Measures pipeline latency from the live SSE stream.
 *
 * The backend stamps an Alert and its Decision with the same timestamp and does
 * not persist flow-capture time, so these latencies can't be read from the
 * database. The stream does carry every stage in order for each dispatched flow:
 *
 *   capture{src_ip} → detect_ml → [detect_rate_rule] → score{incident_hint, tier}
 *     → correlate → alert → policy → decision → playbook → audit
 *
 * Pairing them by source IP gives, per flow:
 *   detection  = alert.receivedAt    - capture.receivedAt   (MTTD)
 *   decision   = decision.receivedAt - capture.receivedAt   (per tier)
 * Measured on arrival in this browser, so they include SSE transport time.
 */
export class LatencyTracker {
  private lastCapture = new Map<string, number>();
  private pending: { src: string; tier: Severity | null; capturedAt: number; detected: boolean } | null = null;
  readonly detection: { at: number; ms: number }[] = [];
  readonly decision: { at: number; ms: number; tier: Severity }[] = [];

  constructor(private maxSamples = 500) {}

  feed(e: PipelineEvent) {
    const p = e.payload;
    switch (e.stage) {
      case 'capture':
        if (typeof p.src_ip === 'string') this.lastCapture.set(p.src_ip, e.receivedAt);
        break;
      case 'score': {
        const src = typeof p.incident_hint === 'string' ? p.incident_hint : null;
        const capturedAt = src ? this.lastCapture.get(src) : undefined;
        this.pending = src && capturedAt !== undefined
          ? { src, tier: normalizeTier(p.tier as string), capturedAt, detected: false }
          : null;
        break;
      }
      case 'alert':
        if (this.pending && !this.pending.detected) {
          this.push(this.detection, { at: e.receivedAt, ms: e.receivedAt - this.pending.capturedAt });
          this.pending.detected = true;
        }
        break;
      case 'decision':
        if (this.pending?.tier) {
          this.push(this.decision, { at: e.receivedAt, ms: e.receivedAt - this.pending.capturedAt, tier: this.pending.tier });
        }
        this.pending = null;
        break;
    }
  }

  medianDetectionMs() { return median(this.detection.map((s) => s.ms)); }

  decisionByTier(tier: Severity) {
    const xs = this.decision.filter((s) => s.tier === tier).map((s) => s.ms);
    return { medianMs: median(xs), samples: xs.length };
  }

  private push<T>(arr: T[], v: T) {
    arr.push(v);
    if (arr.length > this.maxSamples) arr.shift();
  }
}
