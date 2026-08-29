import { defineConfig } from "orval";

export default defineConfig({
  yunoApi: {
    input: {
      target: "../api/openapi.json",
    },
    output: {
      target: "./src/lib/api/generated/api.ts",
      schemas: "./src/lib/api/generated/models",
      client: "react-query",
      httpClient: "fetch",
      mode: "single",
      clean: true,
      formatter: "prettier",
      baseUrl: {
        runtime:
          'process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"',
      },
      override: {
        fetch: {
          includeHttpResponseReturnType: false,
        },
        query: {
          signal: true,
          useQuery: true,
        },
        useTypeOverInterfaces: true,
      },
    },
  },
});
