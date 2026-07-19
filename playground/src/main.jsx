import React from "react";
import { createRoot } from "react-dom/client";
import { fromResponse } from "../../packages/javascript/core/browser.js";
import { PROVIDERS, PROBLEM_CONTENT } from "./data.js";
import { ProblemPage, PlaygroundPage, BatchPage, MethodologyPage } from "./pages.jsx";
import "./styles.css";

const page = document.body.dataset.page || "home";
const providerKey = page === "anthropic" ? "anthropic" : page === "gemini" ? "google" : "openai";
const initial = PROVIDERS[providerKey];
const initialLedger = fromResponse(initial.response, {
  provider: providerKey,
  surface: initial.surface,
  model: initial.model,
  priceCards: initial.priceCards,
  debugTrace: true
});

let app;
if (page === "playground") app = <PlaygroundPage />;
else if (page === "batch") app = <BatchPage />;
else if (page === "methodology") app = <MethodologyPage />;
else app = <ProblemPage content={PROBLEM_CONTENT[page] || PROBLEM_CONTENT.home} ledger={initialLedger} providerId={providerKey} />;

createRoot(document.getElementById("root")).render(<React.StrictMode>{app}</React.StrictMode>);
