import {
  defineConfig,
  devices,
  type PlaywrightTestConfig,
} from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const apiURL = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000";
const credentialed = process.env.RUN_OPENAI_CREDENTIALED === "1";
const credentialedProjectRequested = process.argv.some((argument) =>
  argument.includes("chromium-realtime"),
);
const syntheticAudioPath = process.env.OPENAI_REALTIME_SYNTHETIC_WAV_PATH;

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

const webServer: PlaywrightTestConfig["webServer"] =
  process.env.PLAYWRIGHT_SKIP_WEB_SERVER === "1" ||
  (credentialedProjectRequested && !credentialed)
    ? undefined
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
      testIgnore: /.*\.realtime\.credentialed\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
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
