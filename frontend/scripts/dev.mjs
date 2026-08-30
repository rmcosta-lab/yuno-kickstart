import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendDirectory = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "..",
);
const rootEnvPath = resolve(frontendDirectory, "../.env");
const forwardedKeys = new Set([
  "API_BASE_URL",
  "NEXT_PUBLIC_API_BASE_URL",
  "NEXT_PUBLIC_INTAKE_USE_TEST_BOUNDARY",
  "VOLTA_DEMO_BEARER_TOKEN",
]);

if (existsSync(rootEnvPath)) {
  for (const line of readFileSync(rootEnvPath, "utf8").split(/\r?\n/u)) {
    const match = line.match(/^([A-Z][A-Z0-9_]*)=(.*)$/u);
    if (!match || !forwardedKeys.has(match[1]) || process.env[match[1]]) {
      continue;
    }

    const rawValue = match[2].trim();
    const quoted =
      rawValue.length >= 2 &&
      ((rawValue.startsWith('"') && rawValue.endsWith('"')) ||
        (rawValue.startsWith("'") && rawValue.endsWith("'")));
    process.env[match[1]] = quoted ? rawValue.slice(1, -1) : rawValue;
  }
}

const nextBinary = resolve(
  frontendDirectory,
  "node_modules/next/dist/bin/next",
);
const child = spawn(
  process.execPath,
  [nextBinary, "dev", ...process.argv.slice(2)],
  {
    cwd: frontendDirectory,
    env: process.env,
    stdio: "inherit",
  },
);

child.on("exit", (code) => {
  process.exitCode = code ?? 0;
});
