import {
  defineConfig,
  devices,
  type PlaywrightTestConfig,
} from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const apiURL = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000";
const credentialed = process.env.RUN_OPENAI_CREDENTIALED === "1";
const browserTrialProjectRequested = process.argv.some((argument) =>
  argument.includes("chromium-trial"),
);
const credentialedProjectRequested = process.argv.some((argument) =>
  argument.includes("chromium-realtime"),
);
const syntheticAudioPath = process.env.OPENAI_REALTIME_SYNTHETIC_WAV_PATH;
const trialBearer = process.env.VOLTA_DEMO_BEARER_TOKEN ?? "";
const trialDatabaseURL = process.env.VOLTA_TRIAL_DATABASE_URL ?? "";

function isSafeTrialDatabase(value: string) {
  try {
    const parsed = new URL(value);
    return (
      parsed.protocol === "postgresql+asyncpg:" &&
      ["localhost", "127.0.0.1", "[::1]"].includes(parsed.hostname) &&
      parsed.pathname.startsWith("/volta_trial_")
    );
  } catch {
    return false;
  }
}

const trialPrerequisitesAvailable =
  trialBearer.length > 0 && isSafeTrialDatabase(trialDatabaseURL);
const trialBaseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";
const trialApiURL = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8100";

const frontendServer = {
  command: "pnpm dev --hostname localhost --port 3000",
  url: `${baseURL}/sessions`,
  reuseExistingServer: !process.env.CI,
  timeout: 120_000,
  stdout: "ignore" as const,
  stderr: "pipe" as const,
};

const apiServer = {
  command: "cd .. && make dev-api",
  url: `${apiURL}/health`,
  reuseExistingServer: !process.env.CI,
  timeout: 120_000,
  stdout: "ignore" as const,
  stderr: "pipe" as const,
};

const trialFrontendServer = {
  command: "pnpm build && pnpm start --hostname localhost --port 3100",
  url: `${trialBaseURL}/intake`,
  reuseExistingServer: false,
  timeout: 180_000,
  stdout: "ignore" as const,
  stderr: "pipe" as const,
  env: {
    NEXT_PUBLIC_API_BASE_URL: trialApiURL,
  },
};

const trialApiServer = {
  command:
    "cd .. && uv run alembic -c backend/alembic.ini upgrade head && uv run --package yuno-api uvicorn app.main:app --port 8100",
  url: `${trialApiURL}/health`,
  reuseExistingServer: false,
  timeout: 180_000,
  stdout: "ignore" as const,
  stderr: "pipe" as const,
  env: {
    APP_ENV: "test",
    CORS_ORIGINS: JSON.stringify([trialBaseURL]),
    DATABASE_URL: trialDatabaseURL,
    UV_CACHE_DIR: "/tmp/volta-phase17-uv-cache",
    VOLTA_DEMO_BEARER_TOKEN: trialBearer,
    VOLTA_EXTRACTION_MODE: "deterministic",
    VOLTA_MUTATION_RATE_LIMIT_REQUESTS: "200",
  },
};

const webServer: PlaywrightTestConfig["webServer"] =
  process.env.PLAYWRIGHT_SKIP_WEB_SERVER === "1" ||
  (credentialedProjectRequested && !credentialed) ||
  (browserTrialProjectRequested && !trialPrerequisitesAvailable)
    ? undefined
    : browserTrialProjectRequested
      ? [trialApiServer, trialFrontendServer]
      : credentialed
        ? [apiServer, frontendServer]
        : frontendServer;

const realtimeLaunchArgs = [
  "--use-fake-device-for-media-stream",
  "--use-fake-ui-for-media-stream",
];
if (syntheticAudioPath) {
  realtimeLaunchArgs.push(
    `--use-file-for-fake-audio-capture=${syntheticAudioPath}`,
  );
}

export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./test-results",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "line",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    locale: "en-US",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      testIgnore: [
        /.*\.realtime\.credentialed\.spec\.ts/,
        /complete-browser-trial\.spec\.ts/,
      ],
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "chromium-trial",
      testMatch: /complete-browser-trial\.spec\.ts/,
      timeout: 180_000,
      use: {
        ...devices["Desktop Chrome"],
        baseURL: trialBaseURL,
        screenshot: "off",
        trace: "off",
        video: "off",
      },
    },
    {
      name: "chromium-realtime",
      testMatch: /.*\.realtime\.credentialed\.spec\.ts/,
      timeout: 120_000,
      use: {
        ...devices["Desktop Chrome"],
        permissions: ["microphone"],
        launchOptions: { args: realtimeLaunchArgs },
        screenshot: "off",
        trace: "off",
      },
    },
  ],
  webServer,
});
