import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A SOLUÇÃO: Força a criação do server.js e da pasta .next/standalone no build
  output: "standalone",
  // Não anuncia a stack no header X-Powered-By.
  poweredByHeader: false,

  /* config options here */
  experimental: {
    agentFeedback: true,
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
