import React, { useState } from "react";
import { COMPONENT_LABELS } from "./data.js";
import { appPath } from "./paths.js";

export function Header() {
  return (
    <header className="site-header">
      <a className="wordmark" href={appPath("/")} aria-label="RunCost home">RunCost<span>.</span></a>
      <nav aria-label="Primary navigation">
        <a href={appPath("/playground/")}>Playground</a>
        <a href={appPath("/batch/")}>Batch</a>
        <a href={appPath("/methodology/")}>Methodology</a>
        <a href="https://github.com/adamallcock/runcost">GitHub</a>
        <a className="nav-action" href={appPath("/#install")}>Install</a>
      </nav>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="site-footer">
      <a className="wordmark wordmark-small" href={appPath("/")}>RunCost<span>.</span></a>
      <div className="footer-links">
        <a href={appPath("/playground/")}>Playground</a><a href={appPath("/batch/")}>Batch</a>
        <a href={appPath("/methodology/")}>Methodology</a><a href="https://github.com/adamallcock/runcost/issues/57">Cases</a><a href="https://github.com/adamallcock/runcost">GitHub</a>
      </div>
      <p>Open source · MIT License</p>
    </footer>
  );
}

export function ArrowDown() {
  return <svg className="arrow-down" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v16m-6-6 6 6 6-6" /></svg>;
}

export function InstallBand() {
  const [copied, setCopied] = useState(false);
  const command = "pip install runcost-ai  # or: npm install runcost";
  async function copy() {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }
  return (
    <section className="install-band" id="install">
      <div><h2>Install in 60 seconds</h2><p>Run locally or in CI. No account required.</p></div>
      <pre><code>$ pip install runcost-ai{"\n"}$ runcost quote response.json</code></pre>
      <button className="button secondary" type="button" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
    </section>
  );
}

export function ResponsePreview({ ledger }) {
  const rows = ledger?.components || [];
  return (
    <div className="response-preview" aria-label="Example componentized cost ledger">
      <p className="preview-label">Your provider response</p>
      <pre className="preview-code"><code>{`{
  "model": "gpt-4.1-mini",
  "usage": {
    "input_tokens": 1842,
    "cached_tokens": 1024,
    "output_tokens": 1026
  }
}`}</code></pre>
      <ArrowDown />
      <div className="preview-ledger">
        <div className="preview-head"><span>Component</span><span>Quantity</span><span>Cost</span></div>
        {rows.slice(0, 4).map((component) => <div className="preview-row" key={component.name}><span>{COMPONENT_LABELS[component.name]?.[0] || component.name}</span><span>{component.quantity}</span><span>${component.cost}</span></div>)}
      </div>
      <ArrowDown />
      <div className="preview-total"><strong>Exact total</strong><strong>${ledger?.total || "0.00"} USD</strong></div>
      <p className="preview-note">Every selected rate and source remains visible.</p>
    </div>
  );
}

export function ComponentTable({ ledger }) {
  if (!ledger) return null;
  return (
    <div className="table-scroll">
      <table className="component-table">
        <thead><tr><th>Component</th><th>Quantity</th><th>Unit rate (USD)</th><th>Cost (USD)</th></tr></thead>
        <tbody>
          {ledger.components.map((component) => {
            const labels = COMPONENT_LABELS[component.name] || [component.name, component.unit];
            return <tr key={`${component.name}-${component.price_card_id}`}><td><strong>{labels[0]}</strong><small>{labels[1]}</small></td><td>{component.quantity} {component.unit === "token" ? "tokens" : component.unit}</td><td>${component.unit_price} / {component.unit}</td><td><strong>${component.cost}</strong></td></tr>;
          })}
          <tr className="total-row"><td><strong>Total</strong></td><td></td><td></td><td><strong>${ledger.total}</strong></td></tr>
        </tbody>
      </table>
    </div>
  );
}

export function WarningList({ warnings = [] }) {
  return warnings.length === 0
    ? <p className="warning-ok"><span aria-hidden="true">✓</span> No pricing warnings.</p>
    : <ul className="warning-list">{warnings.map((warning, index) => <li key={`${warning.code}-${index}`}><strong>{warning.code}</strong> — {warning.message}</li>)}</ul>;
}

export function Trace({ ledger }) {
  const [open, setOpen] = useState(false);
  const decisions = ledger?.debug_trace?.decisions || [];
  const selected = decisions.filter((decision) => decision.type === "price_component_match");
  return (
    <div className="trace">
      <button className="trace-toggle" type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span>{open ? "−" : "+"} Decision trace</span><span>{decisions.length} recorded decisions</span>
      </button>
      {open && <ol>{selected.map((decision, index) => <li key={index}><span>{decision.component}</span><code>{decision.selected_price_card_id || "unpriced"}</code></li>)}</ol>}
    </div>
  );
}
