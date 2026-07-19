import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const pages = [
  "index.html",
  "playground/index.html",
  "batch/index.html",
  "methodology/index.html",
  "openai-cost-calculator/index.html",
  "anthropic-cost-calculator/index.html",
  "gemini-cost-calculator/index.html",
  "batch-api-cost-calculator/index.html"
];

export default defineConfig({
  base: process.env.VITE_BASE_PATH || "/",
  plugins: [react()],
  build: {
    rollupOptions: {
      input: Object.fromEntries(
        pages.map((page) => [page.replace(/\/index\.html$/, "") || "home", resolve(import.meta.dirname, page)])
      ),
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react")) return "react";
          if (id.includes("packages/javascript/core/browser.js")) return "runcost-core";
          return undefined;
        }
      }
    }
  }
});
