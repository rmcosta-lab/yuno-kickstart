# Set up Codex development tooling

Use this guide to discover, install, configure, and verify the Codex development tools used by this repository. The root `AGENTS.md` defines when to use each tool and the security boundaries that still apply.

## Prerequisites

Install these local prerequisites before configuring Model Context Protocol (MCP) servers that use standard input/output (STDIO):

- A current Node.js Long-Term Support (LTS) release with `npm` and `npx`
- A current stable Chrome installation for Chrome DevTools MCP
- Node.js 18 or newer for Playwright MCP
- The `rtk` command proxy when this guide runs under the repository's Codex user instructions; verify it with `rtk --version`

Run commands from the repository root. The first `npx` invocation may download a package and requires network access.

Examples prefixed with `rtk` are intended for the configured Codex shell. In an environment that does not load the repository owner's user-level RTK instruction, run the underlying command without that prefix.

## Discover the current setup

Check tools in the environment that will execute the task:

1. Run `codex mcp list`.
2. Confirm that each required MCP server is enabled, authenticated when needed, and available in the current session.
3. Run `/skills` in Codex and search for each required skill.
4. Inspect repository-scoped skills:

   ```bash
   rtk rg --files .agents/skills
   ```

5. Run `/plugins` when a task requires a plugin-provided skill, including any `vercel:*` skill.
6. Restart Codex after configuration, skill, or plugin changes.
7. Repeat the checks and make one harmless read-only MCP call as a smoke test.

If a repository `SKILL.md` exists but `/skills` does not list it, restart Codex before attempting another installation. Repeat discovery inside remote and ephemeral environments because a local inventory does not prove that another environment is ready.

## Activate the Context7 MCP server

The repository already declares Context7 as a project-scoped remote MCP server in `.codex/config.toml`:

```toml
[mcp_servers.context7]
type = "http"
url = "https://mcp.context7.com/mcp/oauth"
```

Restart Codex and run `codex mcp list`. Treat Context7 as ready only when the client supports its authentication flow and exposes the library-resolution and documentation-query tools in the current session. Complete the one-time OAuth prompt when the client offers it.

If the server appears as `Auth: Unsupported` or its tools remain absent, do not assume that the project entry is usable. Follow the official client documentation to use the supported Context7 Codex plugin or an API-key remote connection. Request approval before changing shared or global configuration, keep API keys in the environment or secret store, and do not add a second configuration when the project entry works.

Use the `context7-mcp` skill to resolve the official library identifier and fetch current, concept-specific documentation. Yuno and OpenAI keep the source priority defined by the root `AGENTS.md`. See the official [Context7 MCP client documentation](https://context7.com/docs/resources/all-clients) for alternative clients and authentication modes.

## Configure the Yuno MCP server

Yuno documents the official local package `@yuno-payments/yuno-mcp` in its [AI integrations and MCP guide](https://docs.y.uno/docs/ai-capabilities/building-ai-integrations-with-yunos-llms-and-mcp). Configure it at project scope without storing credentials in the repository.

Add this entry to `.codex/config.toml`:

```toml
[mcp_servers.yuno]
command = "npx"
args = ["-y", "@yuno-payments/yuno-mcp@latest"]
env_vars = [
  "YUNO_ACCOUNT_CODE",
  "YUNO_PUBLIC_API_KEY",
  "YUNO_PRIVATE_SECRET_KEY",
  "YUNO_COUNTRY_CODE",
  "YUNO_CURRENCY",
]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60
```

Provide credentials through the local environment or secret store:

```bash
export YUNO_ACCOUNT_CODE="your_yuno_account_code_here"
export YUNO_PUBLIC_API_KEY="your_yuno_public_api_key_here"
export YUNO_PRIVATE_SECRET_KEY="your_yuno_private_secret_key_here"
export YUNO_COUNTRY_CODE="BR"
export YUNO_CURRENCY="BRL"
```

Verify the server after restarting Codex:

```bash
codex mcp list
```

Use the Yuno MCP for current documentation, schema inspection, integration validation, and intentional sandbox experiments. A tool being available does not authorize a payment, refund, cancellation, capture, or other financial mutation.

## Install development MCP servers

Use only the official packages and endpoints in this section. The `codex mcp add` commands below write the default shared Codex configuration described in the [official Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp). For this repository, prefer the project-scoped `.codex/config.toml` entries in the next section. Run a shared configuration command only when the user has approved that scope.

If installation requires interactive OAuth, tell the user and request participation before continuing.

### Install Chrome DevTools MCP

Use the official [Chrome DevTools MCP package](https://github.com/ChromeDevTools/chrome-devtools-mcp).

```bash
codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest
```

### Install Playwright MCP

Use the official [Playwright MCP package](https://github.com/microsoft/playwright-mcp) with an isolated browser profile so cookies and local state are not shared across sessions:

```bash
codex mcp add playwright -- npx -y @playwright/mcp@latest --isolated
```

### Install shadcn MCP

Follow the official [shadcn MCP documentation](https://ui.shadcn.com/docs/mcp).

```bash
codex mcp add shadcn -- npx -y shadcn@latest mcp
```

The repository must contain a valid `components.json` before component installation. The standard shadcn registry requires no additional authentication. Keep private-registry tokens in environment variables.

### Install GitHub MCP

Use the official [GitHub MCP Server](https://github.com/github/github-mcp-server) and bind authentication to an environment variable:

```bash
codex mcp add github --url https://api.githubcopilot.com/mcp/ --bearer-token-env-var GITHUB_PAT_TOKEN
```

Provide `GITHUB_PAT_TOKEN` through the local environment or secret store with the least privileges required for the task. Never place it in `.codex/config.toml`, `AGENTS.md`, source files, logs, screenshots, or tool prompts. The command writes shared Codex configuration, so prefer the project-scoped entry below for this repository.

### Install Supabase MCP

Follow the official [Supabase MCP documentation](https://supabase.com/docs/guides/ai-tools/mcp). Start with documentation-only, read-only access that requires no project reference:

```bash
codex mcp add supabase --url "https://mcp.supabase.com/mcp?read_only=true&features=docs"
```

When a task needs database, debugging, or development tools, configure a specific development project at project scope and complete `codex mcp login supabase`. Do not connect the MCP to production by default. Remove `read_only=true` only for an explicitly requested mutation in a development project or branch. Keep mutating tools approval-gated, review generated SQL, use migrations for durable schema changes, run security and performance advisors, and verify the result.

### Install Vercel MCP

Follow the official [Vercel MCP documentation](https://vercel.com/docs/agent-resources/vercel-mcp).

```bash
codex mcp add vercel --url https://mcp.vercel.com
codex mcp login vercel
```

OAuth may open a browser. Keep Vercel access tokens out of `.codex/config.toml` and committed files.

## Configure MCP servers at project scope

When the command-line interface (CLI) cannot create a project-scoped entry, add the relevant credential-free configuration to `.codex/config.toml`.

### Chrome DevTools

```toml
[mcp_servers.chrome-devtools]
command = "npx"
args = ["-y", "chrome-devtools-mcp@latest"]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60
```

### Playwright

```toml
[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest", "--isolated"]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60
```

### shadcn

```toml
[mcp_servers.shadcn]
command = "npx"
args = ["-y", "shadcn@latest", "mcp"]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60
```

### GitHub

```toml
[mcp_servers.github]
url = "https://api.githubcopilot.com/mcp/"
bearer_token_env_var = "GITHUB_PAT_TOKEN"
enabled = true
tool_timeout_sec = 60
default_tools_approval_mode = "writes"
```

### Supabase

```toml
[mcp_servers.supabase]
url = "https://mcp.supabase.com/mcp?read_only=true&features=docs"
enabled = true
tool_timeout_sec = 60
```

After selecting a development project, replace the docs-only URL with this project-scoped form and substitute the placeholder before enabling the additional tools:

```text
https://mcp.supabase.com/mcp?project_ref=your_project_ref_here&read_only=true&features=docs%2Cdatabase%2Cdebugging%2Cdevelopment
```

Do not commit a real project reference when its disclosure is not intended.

### Vercel

```toml
[mcp_servers.vercel]
url = "https://mcp.vercel.com"
enabled = true
tool_timeout_sec = 60
```

Never place tokens, passwords, or private keys in `.codex/config.toml`. Supply `GITHUB_PAT_TOKEN` and other credentials through the environment or secret store.

## Configure remote environments

Repeat discovery and smoke tests in the actual remote session. A successful local `codex mcp list` is not evidence that the remote environment is ready.

- Prefer official Streamable HTTP servers for GitHub, Supabase, and Vercel
- Complete OAuth in the environment and client that will use the stored session
- Ensure the remote image has Node.js, npm, and browser dependencies before using STDIO servers
- Set `experimental_environment = "remote"` on relevant STDIO servers when the executor supports it
- Use headless, isolated browser profiles when supported
- Forward secrets from the remote secret store with `env_vars` and `source = "remote"` when supported
- Keep all mutating MCP tools approval-gated and within the explicit task scope

If the remote environment cannot launch a browser or receive an OAuth callback, use a browser-capable local or preview environment. Do not copy a personal browser profile, disable sandboxing, or embed credentials as a workaround.

## Install repository-scoped skills

Use `.agents/skills` as the only repository-scoped skill source, following the official [Codex skills scope and discovery rules](https://learn.chatgpt.com/docs/build-skills). Install only skills that are missing and relevant to the task.

### Install the Build Web Apps skills

Source these skills from the official [Build Web Apps plugin](https://github.com/openai/plugins/tree/main/plugins/build-web-apps/skills). Keep only missing `--path` values. The installer stops when a destination directory already exists.

```bash
codex_skill_installer="${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py"

rtk python3 "$codex_skill_installer" \
  --repo openai/plugins \
  --path \
    plugins/build-web-apps/skills/frontend-app-builder \
    plugins/build-web-apps/skills/frontend-testing-debugging \
    plugins/build-web-apps/skills/react-best-practices \
    plugins/build-web-apps/skills/shadcn-best-practices \
    plugins/build-web-apps/skills/supabase-best-practices \
  --dest .agents/skills
```

If the system installer script is unavailable, invoke `$skill-installer` in Codex and provide the same `openai/plugins` repository paths. Do not substitute similarly named community skills.

Two source directory names differ from their declared skill identifiers:

- `shadcn-best-practices` declares `name: shadcn`
- `supabase-best-practices` declares `name: supabase-postgres-best-practices`

Do not rename their frontmatter. Use the identifier displayed by `/skills`. Ignore the bundle's Stripe guidance because Yuno is this project's payment orchestration layer.

### Install standalone design and writing skills

Install missing skills from the official [Anthropic frontend design source](https://github.com/anthropics/skills/tree/main/skills/frontend-design) and [Vercel Labs agent skills](https://github.com/vercel-labs/agent-skills) at project scope:

```bash
rtk npx skills add anthropics/skills --skill frontend-design
rtk npx skills add vercel-labs/agent-skills --skill web-design-guidelines
rtk npx skills add vercel-labs/agent-skills --skill writing-guidelines
```

Select Codex and project scope in the installer. Use global scope only when the user requests the skill for every repository.

`openai-docs` is a Codex system skill. Do not install a repository duplicate. If it is missing, restart Codex, update Codex through its supported distribution, and check `/skills` again.

### Install the Vercel plugin skills

The `vercel:*` identifiers come from the [official Vercel plugin source](https://github.com/openai/plugins/tree/main/plugins/vercel) distributed through the Codex Plugin Directory:

1. Run `/plugins` in Codex.
2. Search for `Vercel` under **Developer Tools**.
3. Confirm that the source is the official Codex directory entry.
4. Select **Install Plugin** or **Enable**.
5. Restart Codex.
6. Run `/skills` and confirm the required identifiers: `vercel:ai-sdk`, `vercel:nextjs`, `vercel:react-best-practices`, `vercel:shadcn`, `vercel:agent-browser-verify`, and `vercel:verification`.

Do not copy Vercel plugin cache directories into the repository. The plugin manager owns installation and updates.

## Verify repository-scoped skills

Validate managed symlinks without changing files:

```bash
uvx library-skills --check
```

Do not pass `--claude` because this repository does not maintain `.claude/skills`.

Check the metadata of every installed skill:

```bash
rtk rg -n '^name:|^description:' .agents/skills/*/SKILL.md
```

Treat a missing file, invalid frontmatter, or absent `/skills` entry as an incomplete installation. Use the [official OpenAI plugin catalog](https://github.com/openai/plugins) as the source for Build Web Apps skills, not the deprecated `openai/skills` repository.
