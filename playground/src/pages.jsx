import React, { useEffect, useMemo, useRef, useState } from "react";
import { fromBatchResults, fromResponse, fromResponseAuto } from "../../packages/javascript/core/browser.js";
import { BATCH_CASES, COMPONENT_LABELS, PROVIDERS, PROVIDER_FIXTURES } from "./data.js";
import { ComponentTable, Footer, Header, InstallBand, ResponsePreview, Trace, WarningList } from "./components.jsx";
import { appPath } from "./paths.js";

const EXAMPLE_PRICE_PROMISES = new Map();

function warningKey(warning) {
  return `${warning.code}:${JSON.stringify(warning.metadata || {})}`;
}

function mergeWarnings(...groups) {
  const seen = new Set();
  return groups.flat().filter((warning) => {
    const key = warningKey(warning);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

async function priceWithExternalSources(id, selectedModel, response, memoize = false) {
  const config = PROVIDERS[id];
  const cacheKey = memoize ? `${id}:${selectedModel}:${JSON.stringify(response)}` : null;
  if (cacheKey && EXAMPLE_PRICE_PROMISES.has(cacheKey)) return EXAMPLE_PRICE_PROMISES.get(cacheKey);
  const task = (async () => {
    try {
      const automatic = await fromResponseAuto(response, {
        provider: id,
        surface: config.surface,
        model: selectedModel,
        debugTrace: true
      });
      if (automatic.metadata?.price_resolution?.selected_source) {
        automatic.metadata.playground_price_mode = "external";
        return automatic;
      }
      const fallback = fromResponse(response, {
        provider: id,
        surface: config.surface,
        model: selectedModel,
        priceCards: config.priceCards,
        debugTrace: true
      });
      fallback.metadata = {
        ...(fallback.metadata || {}),
        price_resolution: automatic.metadata?.price_resolution,
        playground_price_mode: "offline_example"
      };
      fallback.warnings = mergeWarnings(fallback.warnings || [], automatic.warnings || []);
      return fallback;
    } catch (error) {
      const fallback = fromResponse(response, {
        provider: id,
        surface: config.surface,
        model: selectedModel,
        priceCards: config.priceCards,
        debugTrace: true
      });
      fallback.metadata = { ...(fallback.metadata || {}), playground_price_mode: "offline_example" };
      fallback.warnings = mergeWarnings(fallback.warnings || [], [{
        code: "price_source_unavailable",
        message: "External price sources could not be resolved; the dated playground example rate was used when it matched.",
        metadata: { source: "genai-prices,models.dev,litellm", status: "playground_fallback" }
      }]);
      return fallback;
    }
  })();
  if (cacheKey) EXAMPLE_PRICE_PROMISES.set(cacheKey, task);
  return task;
}

function pricingMode(ledger) {
  return ledger?.metadata?.playground_price_mode === "external" ? "External source (live or cached)" : "Dated offline demo fallback";
}

export function ProblemPage({ content, ledger: initialLedger, providerId }) {
  const [ledger, setLedger] = useState(initialLedger);
  const [refreshing, setRefreshing] = useState(true);
  useEffect(() => {
    let active = true;
    const config = PROVIDERS[providerId];
    priceWithExternalSources(providerId, config.model, config.response, true).then((nextLedger) => {
      if (active) {
        setLedger(nextLedger);
        setRefreshing(false);
      }
    });
    return () => { active = false; };
  }, [providerId]);
  return (
    <><div className="page-shell"><Header />
      <main>
        <section className="problem-hero">
          <div className="hero-copy"><h1>{content.heading}</h1><p>{content.body}</p><div className="hero-actions"><a className="button primary" href={appPath("/playground/")}>Explain a response</a><a className="text-link" href="#install">View the 60-second install</a></div></div>
          <ResponsePreview ledger={ledger} />
        </section>
        <section className="evidence-grid">
          <div>
            <h2>Where estimates go wrong</h2>
            <div className="table-scroll"><table className="comparison-table"><thead><tr><th>Factor</th><th>Naive estimate</th><th>RunCost ledger</th></tr></thead><tbody>
              <tr><td>Cached input</td><td>Charged at full input rate</td><td>Billed at its cache-read rate</td></tr>
              <tr><td>Reasoning output</td><td>Folded into completion</td><td>Retained as its own dimension</td></tr>
              <tr><td>Tools and media</td><td>Usually ignored</td><td>Counted when a rate exists</td></tr>
              <tr><td>Batch and tiers</td><td>Flat-rate assumption</td><td>Matched to the service mode</td></tr>
              <tr><td>Sources</td><td>Unknown</td><td>Every line names its rate card</td></tr>
            </tbody></table></div>
            <h2 className="provider-heading">One contract across providers</h2>
            <div className="provider-rail"><a href={appPath("/openai-cost-calculator/")}>OpenAI</a><a href={appPath("/anthropic-cost-calculator/")}>Anthropic</a><a href={appPath("/gemini-cost-calculator/")}>Gemini</a><span>Bedrock</span><span>Vertex</span><span>Kimi</span></div>
            <p className="rail-note">The response shape changes. The componentized ledger does not.</p>
          </div>
          <aside className="evidence-aside"><h2>Evidence, not a black box</h2>
            <dl><div><dt>Methodology</dt><dd><a href={appPath("/methodology/")}>Usage → rate → ledger</a></dd></div><div><dt>Rate source</dt><dd>{ledger.price_sources?.[0]?.name || "No matching source"}</dd></div><div><dt>Resolution</dt><dd>{refreshing ? "Checking external sources…" : pricingMode(ledger)}</dd></div><div><dt>Pricing snapshot</dt><dd>{ledger.price_sources?.[0]?.retrieved_at || "Unavailable"}</dd></div><div><dt>Example</dt><dd>{content.provider}</dd></div><div><dt>Notice</dt><dd>Warnings stay visible when evidence is missing or ambiguous.</dd></div></dl>
          </aside>
        </section>
        <InstallBand />
      </main><Footer /></div></>
  );
}

export function PlaygroundPage() {
  const [providerId, setProviderId] = useState("openai");
  const [model, setModel] = useState(PROVIDERS.openai.model);
  const [responseText, setResponseText] = useState(JSON.stringify(PROVIDERS.openai.response, null, 2));
  const [ledger, setLedger] = useState(() => price("openai", PROVIDERS.openai.model, PROVIDERS.openai.response));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const requestVersion = useRef(0);
  const provider = PROVIDERS[providerId];

  function price(id, selectedModel, response) {
    const config = PROVIDERS[id];
    return fromResponse(response, { provider: id, surface: config.surface, model: selectedModel, priceCards: config.priceCards, debugTrace: true });
  }
  async function refreshPrice(id, selectedModel, response, memoize = false) {
    const version = ++requestVersion.current;
    setLoading(true);
    try {
      const nextLedger = await priceWithExternalSources(id, selectedModel, response, memoize);
      if (requestVersion.current === version) {
        setLedger(nextLedger);
        setError("");
      }
    } catch (exception) {
      if (requestVersion.current === version) setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      if (requestVersion.current === version) setLoading(false);
    }
  }
  useEffect(() => {
    refreshPrice("openai", PROVIDERS.openai.model, PROVIDERS.openai.response, true);
  }, []);
  function selectProvider(id) {
    const config = PROVIDERS[id];
    setProviderId(id); setModel(config.model); setResponseText(JSON.stringify(config.response, null, 2)); setLedger(price(id, config.model, config.response)); setError("");
    refreshPrice(id, config.model, config.response, true);
  }
  async function submit(event) {
    event.preventDefault();
    try { const parsed = JSON.parse(responseText); await refreshPrice(providerId, model, parsed); }
    catch (exception) { setError(exception instanceof Error ? exception.message : String(exception)); }
  }
  function formatJSON() {
    try { setResponseText(JSON.stringify(JSON.parse(responseText), null, 2)); setError(""); }
    catch (exception) { setError(exception instanceof Error ? exception.message : String(exception)); }
  }
  return (
    <><div className="page-shell tool-page"><Header /><main>
      <form className="tool-grid" onSubmit={submit}>
        <section className="input-pane"><p className="section-number">1. Provider response</p>
          <div className="control-grid"><label>Provider<select value={providerId} onChange={(event) => selectProvider(event.target.value)}>{Object.entries(PROVIDERS).map(([id, config]) => <option key={id} value={id}>{config.label}</option>)}</select></label><label>Endpoint<select value={provider.surface} disabled><option>{provider.endpointLabel}</option></select></label><label>Model<input value={model} onChange={(event) => setModel(event.target.value)} /></label></div>
          <label className="fixture-control">Fixture<select value={providerId} onChange={(event) => selectProvider(event.target.value)}>{PROVIDER_FIXTURES.map((fixture) => <option key={fixture.id} value={fixture.id}>{fixture.label}</option>)}</select></label>
          <div className="editor-label"><label htmlFor="response-editor">Sanitized provider response (paste JSON)</label><button type="button" onClick={formatJSON}>Format JSON</button></div>
          <textarea id="response-editor" spellCheck="false" value={responseText} onChange={(event) => setResponseText(event.target.value)} aria-describedby="privacy-note editor-error" />
          {error && <p className="editor-error" id="editor-error" role="alert">Invalid response: {error}</p>}
          <p className="privacy-note" id="privacy-note">The response stays in this browser. RunCost only downloads public price catalogs; do not paste secrets or private content.</p>
          <button className="button primary submit-button" type="submit" disabled={loading}>{loading ? "Resolving prices…" : "Explain cost"}</button>
        </section>
        <section className="result-pane" aria-live="polite"><p className="section-number">2. Cost breakdown</p><p className="total-label">Calculated total (USD)</p><p className="exact-total">${ledger.total}</p><p className="total-explanation">Calculated for <strong>{ledger.model.billed}</strong> on {provider.label} {provider.endpointLabel} using the rates and usage dimensions below.</p>
          <ComponentTable ledger={ledger} />
          <div className="source-line"><span>Source: <a href={ledger.price_sources?.[0]?.url || appPath("/methodology/")}>{ledger.price_sources?.map((source) => source.name).join(", ") || "No matching source"}</a></span><span>{pricingMode(ledger)}</span><span>Retrieved: {ledger.price_sources?.[0]?.retrieved_at || "—"}</span></div>
          <div className="result-section"><p className="section-number">3. Pricing warnings</p><WarningList warnings={ledger.warnings} /></div>
          <div className="result-section"><p className="section-number">4. How this was calculated</p><Trace ledger={ledger} /></div>
        </section>
      </form>
      <BatchWorkbench compact />
    </main><Footer /></div></>
  );
}

function calculateBatch(batchCase) {
  const input = batchCase.input;
  return fromBatchResults(input.items, {
    provider: input.provider,
    endpoint: input.endpoint,
    model: input.model,
    batchId: input.batch_id,
    priceCards: batchCase.priceCards,
    attribution: { feature: "public-playground" }
  });
}

function BatchWorkbench({ compact = false }) {
  const [selectedId, setSelectedId] = useState(BATCH_CASES[0].id);
  const selected = BATCH_CASES.find((candidate) => candidate.id === selectedId);
  const ledger = useMemo(() => calculateBatch(selected), [selected]);
  return (
    <section className={`batch-workbench ${compact ? "batch-compact" : ""}`}>
      <div className="batch-heading"><div><p className="section-number">{compact ? "5. Batch endpoints" : "Batch result ledger"}</p>{!compact && <h1>One itemized contract across batch APIs.</h1>}</div>{compact && <a className="button secondary" href={appPath("/batch/")}>View full batch ledger</a>}</div>
      <div className="batch-tabs" role="tablist" aria-label="Batch provider">{BATCH_CASES.map((item) => <button type="button" role="tab" aria-selected={selectedId === item.id} key={item.id} onClick={() => setSelectedId(item.id)}>{item.label}</button>)}</div>
      <div className="batch-summary"><span><strong>{ledger.summary.total}</strong> items</span><span className="success"><strong>{ledger.summary.succeeded}</strong> succeeded</span><span className="failure"><strong>{ledger.summary.failed}</strong> failed</span><span><strong>{ledger.summary.pending}</strong> pending</span><span className="batch-total"><strong>${ledger.summary.total_cost}</strong> total</span></div>
      <div className="table-scroll"><table className="batch-table"><thead><tr><th>Item ID</th><th>Status</th><th>Model</th><th>Endpoint</th><th>Cost (USD)</th></tr></thead><tbody>{ledger.items.map((item) => <tr key={item.id}><td><code>{item.id}</code></td><td><span className={`status ${item.status}`}>{item.status}</span></td><td>{item.ledger?.model?.billed || selected.input.model || "—"}</td><td><code>{item.metadata?.endpoint || selected.input.endpoint || ledger.surface}</code></td><td>{item.ledger ? `$${item.ledger.total}` : "—"}</td></tr>)}</tbody></table></div>
      {ledger.warnings.length > 0 && <WarningList warnings={ledger.warnings} />}
    </section>
  );
}

export function BatchPage() {
  return <><div className="page-shell"><Header /><main className="batch-page"><BatchWorkbench /><section className="batch-notes"><h2>Failures are part of the ledger.</h2><p>RunCost never drops failed or pending records to make a batch total look complete. Each provider result is unwrapped into the same succeeded, errored, or pending item contract; only successful items contribute cost.</p><a className="text-link" href="https://github.com/adamallcock/runcost/blob/main/docs/internal/decisions/2026-07-15-batch-and-expansion-contracts.md">Read the batch contract</a></section></main><Footer /></div></>;
}

export function MethodologyPage() {
  return <><div className="page-shell"><Header /><main className="methodology-page"><header><h1>Evidence, not a black box.</h1><p>RunCost separates extraction, price selection, and exact decimal arithmetic so every result can be explained, tested, and reproduced.</p></header>
    <section className="method-steps"><article><span>01</span><h2>Normalize usage</h2><p>Provider and framework adapters map response fields into named billing components. Inclusive totals are netted only when the relationship is explicit.</p></article><article><span>02</span><h2>Select a dated rate</h2><p>Provider, surface, model alias, service mode, region, effective date, and conditional thresholds are matched with deterministic precedence.</p></article><article><span>03</span><h2>Calculate exactly</h2><p>Decimal arithmetic prices each component independently. Discounts are separate ledger entries rather than invisible mutations.</p></article><article><span>04</span><h2>Preserve uncertainty</h2><p>Unknown models, stale sources, unpriced dimensions, ambiguous inclusive counts, and provider-cost disagreements remain visible warnings.</p></article></section>
    <section className="method-proof"><h2>Three implementations, one fixture truth.</h2><p>Python, JavaScript/TypeScript, and Go run the same shared fixtures. The generated conformance report labels preserved, warned, unsupported, and not-yet-tested pathways instead of claiming blanket support.</p><div className="method-links"><a className="button primary" href="https://github.com/adamallcock/runcost/blob/main/docs/generated/conformance-report.md">Open conformance report</a><a className="text-link" href="https://github.com/adamallcock/runcost/tree/main/schemas">Inspect JSON Schemas</a></div></section>
    <section className="precedence"><h2>Default source precedence</h2><ol><li>Explicit user or contract prices</li><li><code>genai-prices</code></li><li><code>models.dev</code></li><li>LiteLLM pricing data</li><li>Compatibility warnings when no safe match exists</li></ol><p>OpenRouter requests try the OpenRouter models API first. RunCost selects one source per calculation, records cache and freshness metadata, and never silently merges competing catalogs. The published packages contain no provider price database.</p></section>
  </main><Footer /></div></>;
}
