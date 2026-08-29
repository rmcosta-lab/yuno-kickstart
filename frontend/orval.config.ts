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
      headers: true,
      baseUrl: {
        runtime:
          'process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"',
      },
      override: {
        mutator: {
          path: "./src/lib/api/volta-fetch.ts",
          name: "voltaFetch",
        },
        fetch: {
          forceSuccessResponse: true,
          includeHttpResponseReturnType: true,
        },
        query: {
          signal: true,
        },
        operations: {
          acknowledge_notification: {
            query: { useMutation: true, useQuery: false },
          },
          approve_operation: {
            query: { useMutation: true, useQuery: false },
          },
          attach_commitment_evidence: {
            query: { useMutation: true, useQuery: false },
          },
          create_call_brief: {
            query: { useMutation: true, useQuery: false },
          },
          create_candidate_commitment: {
            query: { useMutation: true, useQuery: false },
          },
          create_escalation: {
            query: { useMutation: true, useQuery: false },
          },
          create_operation_draft: {
            query: { useMutation: true, useQuery: false },
          },
          create_simulated_recap: {
            query: { useMutation: true, useQuery: false },
          },
          get_operation: {
            query: { useMutation: false, useQuery: true },
          },
          get_operation_audit: {
            query: { useMutation: false, useQuery: true },
          },
          record_quote: {
            query: { useMutation: true, useQuery: false },
          },
          replace_mandate: {
            query: { useMutation: true, useQuery: false },
          },
          start_inbound_simulation: {
            query: { useMutation: true, useQuery: false },
          },
          start_negotiation: {
            query: { useMutation: true, useQuery: false },
          },
        },
        useTypeOverInterfaces: true,
      },
    },
  },
});
