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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-[rgba(26,21,24,0.98)] border-[3px] border-[#0d0d11] shadow-[8px_8px_0px_#0d0d11] rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Neobrutalist Modal Header */}
        <div className="flex items-center justify-between p-6 border-b-[2.5px] border-[#0d0d11] bg-[#1d171b]">
          <div>
            <span className="text-xs font-mono uppercase font-bold text-[var(--torii-amber)] tracking-wider">
              Incident Forensic Detail
            </span>
            <h3 className="text-2xl font-extrabold uppercase text-white tracking-tight mt-0.5">
              Incident #{detailId}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-10 w-10 rounded-full bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] flex items-center justify-center text-[#0d0d11] hover:bg-white active:translate-x-[1px] active:translate-y-[1px] active:shadow-[1px_1px_0px_#0d0d11] transition-all cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm">
          {loading && (
            <div className="flex items-center justify-center py-16 text-[var(--torii-amber)] font-mono font-bold uppercase gap-3">
              <RefreshCw className="h-5 w-5 animate-spin text-[var(--torii-vermilion)]" />
              <span>Fetching forensic telemetry from database...</span>
            </div>
          )}

          {!loading && detail && (
            <>
              {/* Decision & Response - Tactile Card */}
              {detail.decisions?.length > 0 && (() => {
                const d = detail.decisions[0];
                const guards =
                  d.guardrail_results && typeof d.guardrail_results === 'object'
                    ? Object.entries(d.guardrail_results)
                    : [];

                return (
                  <div className="bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[4px_4px_0px_#0d0d11] rounded-2xl p-5">
                    <div className="flex items-center gap-2 text-[#0d0d11] font-extrabold uppercase text-sm mb-4">
                      <Gauge size={18} className="text-[var(--torii-vermilion)]" />
                      <span>Autonomous Decision &amp; Response Pipeline</span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs mb-4">
                      <div className="bg-white p-3 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
                        <span className="text-[#544d49] block text-[11px] font-bold uppercase font-mono">Rule</span>
                        <b className="text-[#0d0d11] font-mono mt-0.5 block">{d.rule_id || '—'}</b>
                      </div>
                      <div className="bg-white p-3 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
                        <span className="text-[#544d49] block text-[11px] font-bold uppercase font-mono">Severity Tier</span>
                        <b className="text-[#0d0d11] font-mono mt-0.5 block">{d.tier}</b>
                      </div>
                      <div className="bg-white p-3 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
                        <span className="text-[#544d49] block text-[11px] font-bold uppercase font-mono">Mode</span>
                        <b className="text-[#0d0d11] uppercase font-mono mt-0.5 block">{d.mode}</b>
                      </div>
                      <div className="bg-white p-3 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
                        <span className="text-[#544d49] block text-[11px] font-bold uppercase font-mono">Status</span>
                        <b className="text-[#0d0d11] uppercase font-mono mt-0.5 block">{d.status}</b>
                      </div>
                      <div className="bg-white p-3 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
                        <span className="text-[#544d49] block text-[11px] font-bold uppercase font-mono">Risk Score</span>
                        <b className="text-[var(--torii-vermilion)] font-mono font-extrabold mt-0.5 block">
                          {Number(d.risk_score).toFixed(1)} / 100
                        </b>
                      </div>
                      <div className="bg-white p-3 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
                        <span className="text-[#544d49] block text-[11px] font-bold uppercase font-mono">Playbook ID</span>
                        <b className="text-[#0d0d11] font-mono mt-0.5 block">{d.playbook_id || '—'}</b>
                      </div>
                    </div>

                    {/* Guardrails verification */}
                    {guards.length > 0 && (
                      <div className="mt-4 pt-3 border-t-[1.5px] border-[#0d0d11]">
                        <span className="text-[11px] text-[#544d49] block mb-2 font-mono font-bold uppercase">
                          Safety Guardrails Verification
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {guards.map(([k, v]: [string, any]) => {
                            const passed = v && typeof v === 'object' ? v.passed : !!v;
                            return (
                              <span
                                key={k}
                                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono font-bold border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] ${
                                  passed
                                    ? 'bg-[var(--torii-sage)] text-white'
                                    : 'bg-[var(--torii-vermilion)] text-white'
                                }`}
                              >
                                {passed ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
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
                      <div className="mt-4 p-3.5 bg-white border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] rounded-xl text-xs text-[#0d0d11] font-mono leading-relaxed">
                        {typeof d.explanation === 'string'
                          ? d.explanation
                          : JSON.stringify(d.explanation)}
                      </div>
                    )}

                    {/* Actions list */}
                    {d.actions?.length > 0 && (
                      <div className="mt-4 pt-4 border-t-[1.5px] border-[#0d0d11] space-y-2">
                        <span className="text-[11px] text-[#544d49] block font-mono font-bold uppercase">
                          Firewall &amp; Response Executions
                        </span>
                        {d.actions.map((a: any) => (
                          <div
                            key={a.id}
                            className="flex items-center justify-between p-3 rounded-xl bg-white border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] text-xs font-mono"
                          >
                            <span className="font-bold text-[#0d0d11]">{a.action}</span>
                            <span className="text-[#544d49]">
                              {a.executor}
                              {a.dry_run ? ' • dry-run' : ''}
                            </span>
                            <span
                              className={`px-2.5 py-0.5 rounded-md text-[11px] uppercase font-bold border-[1px] border-[#0d0d11] ${
                                a.status === 'applied' || a.status === 'executed'
                                  ? 'bg-[var(--torii-sage)] text-white'
                                  : 'bg-[#faf6f0] text-[#0d0d11]'
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
              <div className="bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[4px_4px_0px_#0d0d11] rounded-2xl p-5">
                <div className="flex items-center gap-2 text-[#0d0d11] font-extrabold uppercase text-sm mb-4">
                  <FileText size={18} className="text-[var(--torii-sage)]" />
                  <span>ML Detections &amp; Probability Vectors ({detail.alerts?.length || 0})</span>
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
                        className="p-4 bg-white border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] rounded-xl space-y-3"
                      >
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span
                            className={`px-3 py-1 rounded-md text-xs font-mono font-bold border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] ${
                              a.label?.toLowerCase().includes('benign')
                                ? 'bg-[var(--torii-sage)] text-white'
                                : 'bg-[var(--torii-vermilion)] text-white'
                            }`}
                          >
                            {a.label}
                          </span>
                          <span className="text-xs font-mono font-bold text-[#544d49]">
                            conf {fmtConf(a.confidence)} • margin {Number(a.margin || 0).toFixed(2)}
                          </span>
                          <span className="text-xs text-[#544d49] font-mono font-bold uppercase">
                            {ruleBased ? '⚡ rate-rule' : '🧠 ' + (a.model_version || 'random-forest')}
                          </span>
                        </div>

                        {/* Probability bars */}
                        {probs.length > 0 ? (
                          <div className="space-y-1.5 pt-2">
                            {probs.map(([cls, p]: [string, any]) => (
                              <div key={cls} className="flex items-center gap-3 text-xs font-mono">
                                <span className="w-28 text-[#544d49] font-bold truncate">{cls}</span>
                                <div className="flex-1 h-3 bg-[#f0e9df] border border-[#0d0d11] rounded-md overflow-hidden shadow-[inset_1px_1px_0px_rgba(0,0,0,0.15)]">
                                  <div
                                    className="h-full bg-[var(--torii-vermilion)] rounded-sm transition-all duration-300"
                                    style={{ width: `${(p * 100).toFixed(1)}%` }}
                                  />
                                </div>
                                <span className="w-10 text-right font-bold text-[#0d0d11]">
                                  {(p * 100).toFixed(0)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-[#706764] italic">
                            deterministic rule — no probability distribution.
                          </div>
                        )}

                        <div className="text-[11px] font-mono text-[#706764] pt-2 border-t-[1.5px] border-[#0d0d11]">
                          {a.ts?.replace('T', ' ').slice(0, 19)} • {a.src_ip}:{a.src_port} → {a.dst_ip}:{a.dst_port}
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
