import type { MouseEvent } from 'react';
import './landing.css';
import { ToriiMark } from '../brand/ToriiMark';

/* ---------------------------------------------------------------- pipeline */

function Node({ step, name, sub, text }: { step: string; name: string; sub?: string; text?: string }) {
  return (
    <li className="lp-node">
      <span className="lp-node-step" aria-hidden="true">{step}</span>
      <p className="lp-node-name">{name}</p>
      {sub && <p className="lp-node-sub">{sub}</p>}
      {text && <p className="lp-node-text">{text}</p>}
    </li>
  );
}

const Wire = ({ narrowOnly = false }: { narrowOnly?: boolean }) => (
  <li className={`lp-wire ${narrowOnly ? 'lp-narrow-only' : ''}`} aria-hidden="true" />
);

/** One spine splitting into the two detectors (fork) or joining back (merge). */
function Fork({ merge = false }: { merge?: boolean }) {
  const d = merge
    ? 'M25 0 V22 M75 0 V22 M25 22 H75 M50 22 V44'
    : 'M50 0 V22 M25 22 H75 M25 22 V44 M75 22 V44';
  return (
    <li aria-hidden="true" style={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
      <svg className="lp-fork" viewBox="0 0 100 44" preserveAspectRatio="none"><path d={d} /></svg>
    </li>
  );
}

function Pipeline() {
  return (
    <ol className="lp-pipe" aria-label="Detection and response pipeline, top to bottom">
      <Node step="01" name="NFStream capture" sub="bidirectional flows · libpcap tap"
        text="Meters every flow to the monitored host and maps it to the model's input features." />
      <Fork />
      <Wire narrowOnly />
      <li style={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
        <ul className="lp-pair" aria-label="Parallel detectors">
          <Node step="02a" name="Random Forest IDS" sub="57 features · 5 classes"
            text="Classifies each flow with a probability distribution and a confidence margin." />
          <li className="lp-wire lp-narrow-only" aria-hidden="true" />
          <Node step="02b" name="Rate-rule engine" sub="SYN flood · brute force"
            text="Counts packets and short flows across a time window to catch attacks no single flow shows." />
        </ul>
      </li>
      <Fork merge />
      <Wire narrowOnly />
      <Node step="03" name="Threat event" sub="risk score · correlation · alert"
        text="Scores 0–100 from severity, confidence, asset and intel, then folds repeats into one incident." />
      <Wire />
      <Node step="04" name="Decision engine" sub="versioned policy · guardrails"
        text="Matches the first rule by priority and picks monitor, recommend or auto, subject to the global mode." />
      <Wire />
      <li className="lp-branch-row">
        <div className="lp-node" style={{ listStyle: 'none' }}>
          <span className="lp-node-step" aria-hidden="true">05</span>
          <p className="lp-node-name">Playbook</p>
          <p className="lp-node-sub">dry-run · simulated · lab executor</p>
          <p className="lp-node-text">Runs the steps the policy named: notify, open a case, or contain.</p>
        </div>
        <div className="lp-branch">
          <span className="lp-branch-line" aria-hidden="true" />
          <p className="lp-note">
            <strong>Containment</strong>
            Block, isolate or rate-limit the source. Each rule carries a TTL and is lifted when it expires.
          </p>
        </div>
      </li>
      <Wire />
      <Node step="06" name="Hash-chained audit" sub="SHA-256 · append-only"
        text="Every decision and action is chained to the previous entry and can be re-verified end to end." />
      <Wire />
      <Node step="07" name="Analyst console" sub="live event stream · incident drill-down"
        text="Shows each stage as it fires, with approve, contain and release controls." />
    </ol>
  );
}

/* ---------------------------------------------------------------- coverage */

/** Rows mirror config/policies.yaml rules and the playbooks they name (TTLs from the playbook steps). */
const COVERAGE: { family: string; detected: string; rule: string; mode: string; response: string }[] = [
  {
    family: 'DoS flood',
    detected: 'Rate rule for SYN floods, and the model class DoS SYN Flood',
    rule: 'R-DOS', mode: 'recommend',
    response: 'Rate-limit the source for 10 minutes, notify, open a case',
  },
  {
    family: 'Brute force',
    detected: 'Rate rule for repeated short flows to one port, and the model class Dictionary Brute Force',
    rule: 'R-BRUTE', mode: 'auto',
    response: 'Block the source for 15 minutes, tag the asset, notify',
  },
  {
    family: 'Reconnaissance',
    detected: 'Model class Recon Scan',
    rule: 'R-RECON', mode: 'auto',
    response: 'Rate-limit the source for 5 minutes, notify',
  },
  {
    family: 'MITM / ARP spoofing',
    detected: 'Model class MITM ARP Spoofing',
    rule: 'R-MITM', mode: 'recommend',
    response: 'Isolate the host for 30 minutes, notify, open a case',
  },
];

function Coverage() {
  return (
    <>
      <div className="lp-cov" role="table" aria-label="Attack coverage by family">
        <div className="lp-cov-row lp-cov-head" role="row">
          <span role="columnheader">Attack family</span>
          <span role="columnheader">Detected by</span>
          <span role="columnheader">Rule · mode</span>
          <span role="columnheader">Response</span>
        </div>
        {COVERAGE.map((r) => (
          <div className="lp-cov-row" role="row" key={r.rule}>
            <span role="cell" className="lp-cov-family">{r.family}</span>
            <span role="cell" className="lp-cov-text"><span className="lp-cov-k">Detected by</span>{r.detected}</span>
            <span role="cell" className="lp-mono lp-cov-rule">
              <span className="lp-cov-k">Rule · mode</span>{r.rule}<span className={`lp-cov-mode lp-cov-mode--${r.mode}`}>{r.mode}</span>
            </span>
            <span role="cell" className="lp-cov-text"><span className="lp-cov-k">Response</span>{r.response}</span>
          </div>
        ))}
      </div>
      <p className="lp-cov-note">
        Any family escalates to <span className="lp-mono">R-CRIT-AUTO</span>, which blocks and rate-limits the source
        for 15 minutes, when the risk score reaches 80, model confidence is at least 0.85, the margin over the
        runner-up class is at least 0.30, and the source is known-bad or has repeated. <em>Recommend</em> waits for an
        analyst to approve; the global automation mode can downgrade or switch off automatic responses.
      </p>
    </>
  );
}

/* ---------------------------------------------------------------- page */

const CAPABILITIES: [string, string][] = [
  ['Flow capture', 'NFStream reads packets through libpcap and turns them into bidirectional flow records with timing and size statistics.'],
  ['Two detectors', 'A Random Forest assigns each flow one of five classes; a rate-rule engine catches floods and brute force that span many flows.'],
  ['Risk scoring', 'Severity, model confidence, asset criticality and threat intel are weighted into a single score and placed in a low-to-critical tier.'],
  ['Correlation', 'Alerts from the same source and attack family inside a short window are folded into one incident instead of many.'],
  ['Policy decisions', 'Rules in a versioned policy file choose monitor, recommend or automatic response, with a confidence-margin guardrail and a global off switch.'],
  ['Containment with expiry', 'Playbooks block, isolate or rate-limit a source, and a reaper lifts each rule when its time-to-live ends.'],
  ['Hash-chained audit', 'Decisions and actions are appended to a SHA-256 chain, so any edit to the record breaks verification.'],
];

export default function Landing({ onOpenConsole }: { onOpenConsole: () => void }) {
  const openConsole = (e: MouseEvent) => { e.preventDefault(); onOpenConsole(); };

  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-wrap">
          <a className="lp-brand" href="#" aria-label="Rashomon, home">
            <ToriiMark />
            <span className="lp-wordmark">RASHOMON</span>
          </a>
          <nav className="lp-links" aria-label="Primary">
            <a className="lp-link" href="#pipeline">Pipeline</a>
            <a className="lp-link" href="#coverage">Coverage</a>
            <a className="lp-link" href="#capabilities">Capabilities</a>
            <a className="lp-btn lp-btn--solid" href="#console" onClick={openConsole}>Open console</a>
          </nav>
        </div>
      </header>

      <main>
        <section className="lp-hero" aria-labelledby="lp-title">
          <div className="lp-wrap lp-hero-grid">
            <div>
              <p className="lp-eyebrow">Network detection and response</p>
              <h1 className="lp-h1" id="lp-title">Every flow scored, every decision on the record.</h1>
              <p className="lp-lede">
                Rashomon captures network flows, classifies them with a Random Forest and rate rules,
                decides a response from a versioned policy, and writes each step to a hash-chained audit log.
              </p>
              <div className="lp-actions">
                <a className="lp-btn lp-btn--solid" href="#console" onClick={openConsole}>Open the console</a>
                <a className="lp-btn lp-btn--line" href="#pipeline">See the pipeline</a>
              </div>
            </div>
            <div className="lp-hero-mark">
              <ToriiMark size={120} strokeWidth={0.9} />
              <span className="lp-seal" lang="ja" title="Rashōmon">羅生門</span>
            </div>
          </div>
          <div className="lp-wrap">
            <p className="lp-strip" aria-label="Pipeline stages: capture, classify, score, decide, contain, audit">
              {['capture', 'classify', 'score', 'decide', 'contain', 'audit'].map((stage, i) => (
                <span key={stage}>{stage}{i < 5 && <span className="lp-strip-arrow" aria-hidden="true">→</span>}</span>
              ))}
            </p>
          </div>
        </section>

        <section className="lp-section" id="pipeline" aria-labelledby="lp-pipeline">
          <div className="lp-wrap">
            <div className="lp-section-head">
              <p className="lp-section-label">01 · Pipeline</p>
              <div>
                <h2 className="lp-h2" id="lp-pipeline">One path from packet to audit entry.</h2>
                <p className="lp-section-intro">
                  Each captured flow passes through the same stages in the same order. The console shows every
                  stage as it fires, so a decision can always be traced back to the flow that caused it.
                </p>
              </div>
            </div>
            <Pipeline />
          </div>
        </section>

        <section className="lp-section" id="coverage" aria-labelledby="lp-coverage">
          <div className="lp-wrap">
            <div className="lp-section-head">
              <p className="lp-section-label">02 · Coverage</p>
              <div>
                <h2 className="lp-h2" id="lp-coverage">Four attack families, each with its own rule and response.</h2>
                <p className="lp-section-intro">
                  Detections are grouped into families. Each family maps to a policy rule, and each rule names the
                  playbook that runs. Containment always expires on its own.
                </p>
              </div>
            </div>
            <Coverage />
          </div>
        </section>

        <section className="lp-section" id="capabilities" aria-labelledby="lp-caps">
          <div className="lp-wrap">
            <div className="lp-section-head">
              <p className="lp-section-label">03 · Capabilities</p>
              <h2 className="lp-h2" id="lp-caps">What each part does.</h2>
            </div>
            <dl className="lp-caps">
              {CAPABILITIES.map(([name, text]) => (
                <div className="lp-cap" key={name}>
                  <dt className="lp-cap-name">{name}</dt>
                  <dd className="lp-cap-text">{text}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>
      </main>

      <footer className="lp-foot">
        <div className="lp-wrap">
          <div className="lp-foot-id">
            <ToriiMark size={22} />
            <span className="lp-foot-line">rashomon · nfstream → ids → policy → audit</span>
          </div>
          <nav className="lp-foot-links" aria-label="Footer">
            <a className="lp-link" href="#console" onClick={openConsole}>Console</a>
            <a className="lp-link" href="#pipeline">Pipeline</a>
            <a className="lp-link" href="https://github.com/HcDragon/decisionEngineSoc" rel="noreferrer">Source</a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
