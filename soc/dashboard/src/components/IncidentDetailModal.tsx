import React from 'react';
import { X, Gauge, CheckCircle2, AlertTriangle, FileText, RefreshCw } from 'lucide-react';

interface IncidentDetailModalProps {
  detailId: string | number;
  detail: any;
  loading: boolean;
  onClose: () => void;
  fmtConf: (c: number | undefined) => string;
}

export const IncidentDetailModal: React.FC<IncidentDetailModalProps> = ({
  detailId,
  detail,
  loading,
  onClose,
  fmtConf,
}) => {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xl animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-neutral-950/80 backdrop-blur-3xl border border-white/15 rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-black/40 backdrop-blur-xl">
          <div>
            <span className="text-xs font-mono uppercase text-cyan-400">incident forensic detail</span>
            <h3 className="text-xl font-medium text-white tracking-tight">#{detailId}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-9 w-9 rounded-full bg-white/[0.08] hover:bg-white/[0.15] border border-white/10 flex items-center justify-center text-neutral-300 hover:text-white transition-colors cursor-pointer backdrop-blur-md"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm">
          {loading && (
            <div className="flex items-center justify-center py-16 text-neutral-400 gap-3">
              <RefreshCw className="h-5 w-5 animate-spin text-blue-400" />
              <span>fetching forensic records from database...</span>
            </div>
          )}

          {!loading && detail && (
            <>
              {/* Decision & Response */}
              {detail.decisions?.length > 0 && (() => {
                const d = detail.decisions[0];
                const guards =
                  d.guardrail_results && typeof d.guardrail_results === 'object'
                    ? Object.entries(d.guardrail_results)
                    : [];

                return (
                  <div className="bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-2xl p-5 shadow-lg">
                    <div className="flex items-center gap-2 text-white font-medium text-sm mb-4">
                      <Gauge size={16} className="text-cyan-400" />
                      <span>autonomous decision &amp; response pipeline</span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs mb-4">
                      <div className="bg-black/40 p-3 rounded-xl border border-white/10 backdrop-blur-md">
                        <span className="text-neutral-400 block text-[11px]">Rule</span>
                        <b className="text-white font-mono mt-0.5 block">{d.rule_id || '—'}</b>
                      </div>
                      <div className="bg-black/40 p-3 rounded-xl border border-white/10 backdrop-blur-md">
                        <span className="text-neutral-400 block text-[11px]">Severity Tier</span>
                        <b className="text-white font-mono mt-0.5 block">{d.tier}</b>
                      </div>
                      <div className="bg-black/40 p-3 rounded-xl border border-white/10 backdrop-blur-md">
                        <span className="text-neutral-400 block text-[11px]">Mode</span>
                        <b className="text-white uppercase font-mono mt-0.5 block">{d.mode}</b>
                      </div>
                      <div className="bg-black/40 p-3 rounded-xl border border-white/10 backdrop-blur-md">
                        <span className="text-neutral-400 block text-[11px]">Status</span>
                        <b className="text-white uppercase font-mono mt-0.5 block">{d.status}</b>
                      </div>
                      <div className="bg-black/40 p-3 rounded-xl border border-white/10 backdrop-blur-md">
                        <span className="text-neutral-400 block text-[11px]">Risk Score</span>
                        <b className="text-rose-400 font-mono mt-0.5 block">
                          {Number(d.risk_score).toFixed(1)} / 100
                        </b>
                      </div>
                      <div className="bg-black/40 p-3 rounded-xl border border-white/10 backdrop-blur-md">
                        <span className="text-neutral-400 block text-[11px]">Playbook ID</span>
                        <b className="text-white font-mono mt-0.5 block">{d.playbook_id || '—'}</b>
                      </div>
                    </div>

                    {/* Guardrails verification */}
                    {guards.length > 0 && (
                      <div className="mt-3">
                        <span className="text-[11px] text-neutral-400 block mb-2 font-mono uppercase">
                          safety guardrails verification
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {guards.map(([k, v]: [string, any]) => {
                            const passed = v && typeof v === 'object' ? v.passed : !!v;
                            return (
                              <span
                                key={k}
                                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border backdrop-blur-md ${
                                  passed
                                    ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                                    : 'bg-rose-500/15 border-rose-500/40 text-rose-300'
                                }`}
                              >
                                {passed ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                                {k}
                                {v && typeof v === 'object' && v.actual !== undefined
                                  ? `: ${Number(v.actual).toFixed(2)}`
                                  : ''}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {d.explanation && (
                      <div className="mt-4 p-3.5 bg-black/50 border border-white/10 rounded-xl text-xs text-neutral-300 font-mono leading-relaxed backdrop-blur-md">
                        {typeof d.explanation === 'string'
                          ? d.explanation
                          : JSON.stringify(d.explanation)}
                      </div>
                    )}

                    {/* Actions list */}
                    {d.actions?.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-white/10 space-y-2">
                        <span className="text-[11px] text-neutral-400 block font-mono uppercase">
                          firewall &amp; response executions
                        </span>
                        {d.actions.map((a: any) => (
                          <div
                            key={a.id}
                            className="flex items-center justify-between p-2.5 rounded-xl bg-black/40 border border-white/10 text-xs backdrop-blur-md"
                          >
                            <span className="font-mono text-white">{a.action}</span>
                            <span className="text-neutral-400">
                              {a.executor}
                              {a.dry_run ? ' · dry-run' : ''}
                            </span>
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[11px] uppercase font-mono ${
                                a.status === 'applied' || a.status === 'executed'
                                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                  : 'bg-white/10 text-neutral-300'
                              }`}
                            >
                              {a.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Detections / ML Alerts */}
              <div className="bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-2xl p-5 shadow-lg">
                <div className="flex items-center gap-2 text-white font-medium text-sm mb-4">
                  <FileText size={16} className="text-emerald-400" />
                  <span>ml detections &amp; probability vectors ({detail.alerts?.length || 0})</span>
                </div>

                <div className="space-y-4">
                  {(detail.alerts || []).slice(0, 8).map((a: any) => {
                    const probs =
                      a.probabilities && typeof a.probabilities === 'object'
                        ? Object.entries(a.probabilities).sort(
                            (x: any, y: any) => y[1] - x[1]
                          )
                        : [];
                    const ruleBased = (a.model_version || '').startsWith('rate-rule');

                    return (
                      <div
                        key={a.id}
                        className="p-4 bg-black/40 border border-white/10 rounded-xl space-y-3 backdrop-blur-md"
                      >
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-mono font-medium ${
                              a.label?.toLowerCase().includes('benign')
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            }`}
                          >
                            {a.label}
                          </span>
                          <span className="text-xs font-mono text-neutral-400">
                            conf {fmtConf(a.confidence)} · margin {Number(a.margin || 0).toFixed(2)}
                          </span>
                          <span className="text-xs text-neutral-400 font-mono">
                            {ruleBased ? '⚙ rate-rule' : '🧠 ' + (a.model_version || 'random-forest')}
                          </span>
                        </div>

                        {/* Probability bars */}
                        {probs.length > 0 ? (
                          <div className="space-y-1.5 pt-2">
                            {probs.map(([cls, p]: [string, any]) => (
                              <div key={cls} className="flex items-center gap-3 text-xs">
                                <span className="w-24 text-neutral-400 font-mono truncate">{cls}</span>
                                <div className="flex-1 h-2 bg-black/50 border border-white/5 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-300"
                                    style={{ width: `${(p * 100).toFixed(1)}%` }}
                                  />
                                </div>
                                <span className="w-10 text-right font-mono text-neutral-300">
                                  {(p * 100).toFixed(0)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-neutral-500 italic">
                            deterministic rule — no probability distribution.
                          </div>
                        )}

                        <div className="text-[11px] font-mono text-neutral-400 pt-2 border-t border-white/10">
                          {a.ts?.replace('T', ' ').slice(0, 19)} · {a.src_ip}:{a.src_port} → {a.dst_ip}:{a.dst_port}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
