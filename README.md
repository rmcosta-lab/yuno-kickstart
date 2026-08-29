# Yuno × Nauta Hackathon

Monorepo do projeto Yuno × Nauta, organizado em frontend Next.js, interface de programação de aplicações (API)/backend for frontend (BFF) FastAPI e backend/core Python.

## Bootstrap quickstart

This baseline runs a Next.js frontend, a FastAPI boundary, a plain Python core, and local PostgreSQL. It includes the payment adapter contracts but intentionally leaves challenge-specific business logic open.

### Install the prerequisites

Use these tools for local development:

- Python 3.12 or later; `.python-version` selects Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Node.js with [pnpm](https://pnpm.io/)
- Docker with Docker Compose

### Configure and install the repository

Create a local environment file, then install both workspaces:

```bash
cp .env.example .env
make install
```

Keep the Yuno fields empty until you have sandbox credentials. The mock payment gateway supports local tests without external calls.

### Start the local services

Start PostgreSQL once:

```bash
make postgres-up
```

Run the API and frontend in separate terminals:

```bash
make dev-api
```

```bash
make dev-frontend
```

If the Next.js watcher reports `EMFILE` in a low-descriptor environment, use polling for that session:

```bash
WATCHPACK_POLLING=true make dev-frontend
```

Open `http://localhost:3000` for the app and `http://localhost:8000/docs` for the API documentation.

## Application architecture

The browser calls only the FastAPI boundary. FastAPI imports the backend package directly, which keeps deployment small while preserving code boundaries.

```text
Browser / Next.js
        │ HTTPS / generated client
        ▼
API / FastAPI
        │ typed Python calls
        ▼
Backend / Core ── PostgreSQL
        │
        └────────── Yuno API
```

Read [the architecture guide](docs/architecture.md) for layer ownership and the contract flow. The [bootstrap visual concept](docs/design/bootstrap-concept.png) records the frontend design reference used during setup.

## Generate and verify contracts

FastAPI’s OpenAPI document is the browser contract. Regenerate it and the Orval client after changing Pydantic models:

```bash
make generate
```

Run every required check before handing off a change:

```bash
make check
```

That target runs Ruff, pytest, the frontend linter, the TypeScript checker, and the production frontend build. Rendered frontend changes also require browser, console, network, and responsive smoke tests.

## Protect payment credentials

Use `https://api-sandbox.y.uno` until production access is explicitly approved. `YUNO_PRIVATE_SECRET_KEY` and `YUNO_WEBHOOK_HMAC_SECRET` stay server-side, and neither name may use the `NEXT_PUBLIC_` prefix.

Never store or log card numbers, card verification values, private keys, authorization headers, or complete sensitive payloads. The Yuno Web SDK handles browser-side payment tokenization with the public key.

## Activate development MCP servers

The project-scoped `.codex/config.toml` declares official Model Context Protocol (MCP) servers for Yuno, GitHub, browser validation, shadcn, Supabase documentation, and Vercel. It contains no credentials.

Export required tokens through your environment and complete provider OAuth when prompted. Restart Codex after configuration changes, then verify the active session:

```bash
codex mcp list
```

The Supabase entry is documentation-only until a development project is selected. Keep every external mutation inside an explicitly authorized task.

## Skills do projeto

As skills do projeto ficam em `.agents/skills/<nome>/SKILL.md`. Essa é a única fonte de skills mantida pelo repositório.

O Codex pode selecionar uma skill quando a solicitação corresponde à descrição. Para invocá-la diretamente, use `$nome-da-skill`. Use `/skills` para consultar os identificadores disponíveis. Se uma skill recém-adicionada não aparecer, reinicie a sessão do Codex.

Depois de clonar o repositório, instale as dependências antes de validar links simbólicos fornecidos por pacotes:

```bash
uv sync
uvx library-skills --check
```

## Trabalho paralelo por fases

O GitHub fornece somente o estado compartilhado necessário: branches e pull requests. Antes de assumir uma fase, o ambiente precisa ler a branch padrão remota, criar uma branch sem sobrescrever outra existente, publicar commits e consultar ou abrir pull requests. Issues são opcionais.

Se o repositório remoto não estiver disponível, `$start-phase` interrompe porque a fase não pode ser reservada para a equipe. É possível rascunhar notas fora do fluxo, mas não publicá-las como claim. Não use mutex remoto, UUID de tentativa, branch fixa de documentação ou force-push como mecanismo de coordenação.

### Como o roadmap define as fases

`docs/project-specs/roadmap.md` é um grafo de resultados, não uma fila nem um quadro de status. Cada fase declara:

```markdown
### Fase 04 — Resultado da fase

Slug: resultado-da-fase
Depends on: 02
Conflicts with: none
Gate: evidência observável mínima para enviar a fase à revisão
```

- `Slug` usa letras minúsculas, números e hífens.
- `Depends on` contém pré-requisitos que precisam estar concluídos.
- `Conflicts with` contém fases que não podem ficar ativas ao mesmo tempo; o conflito vale nos dois sentidos.
- `Gate` descreve a evidência mínima de validação.
- `none` representa uma lista vazia.
- O número identifica a fase, mas não cria uma dependência implícita.

Não grave responsável, branch, PR, status ou marcador de conclusão no roadmap. Fases futuras podem ser reorganizadas. Depois que uma fase tiver branch ou PR, não altere silenciosamente seu número, nome, slug, dependências, conflitos ou gate. Uma correção exige decisão explícita da equipe.

### Arquivos de especificação

Use `$manage-shared-specs` para criar o baseline antes da primeira fase:

```text
docs/project-specs/
├── mission.md
├── tech-stack.md
├── roadmap.md
└── YYYY-MM-DD-NN-{slug}/
    ├── requirements.md
    ├── plan.md
    └── validation.md
```

Cada documento responde a uma pergunta diferente:

- `mission.md`: por que o produto existe, para quem e qual resultado precisa demonstrar.
- `tech-stack.md`: quais tecnologias e provedores foram escolhidos e por quê.
- `roadmap.md`: quais resultados serão entregues, com dependências, conflitos e gates.
- `docs/architecture.md`: como as camadas e contratos do sistema se relacionam.
- o diretório datado da fase: o que aquela fase exige, como será implementada e como será validada.

As especificações globais continuam editáveis durante o hackathon. Uma mudança necessária somente para uma fase entra no PR da própria fase quando nada precisa depender dela antes desse PR terminar; registre-a em `plan.md` e no corpo do PR. Use uma branch curta `docs/specs-{topic}` quando a decisão for ampla, quando outra fase ativa precisar dela ou quando uma nova fase de pré-requisito tiver que entrar no roadmap antes do PR atual. Avise os responsáveis afetados e mantenha uma pessoa escrevendo cada arquivo compartilhado por vez.

### Estado de uma fase

| Estado | Fato observável |
| --- | --- |
| `DONE` | O PR foi integrado e contém a evidência de validação exigida. |
| `REVIEW` | Existe um PR aberto da branch da fase. |
| `ACTIVE` | Existe a branch remota da fase e nenhum PR está aberto ou integrado; isso inclui a recuperação de um PR fechado sem merge. |
| `BLOCKED` | Alguma dependência não está `DONE` ou uma fase conflitante está ativa. |
| `READY` | Dependências concluídas, nenhum conflito ativo e nenhuma branch ou história de PR para a fase. |

A branch `phase/NN-{slug}` é a reserva prática da fase. O primeiro commit remoto já deve conter o responsável em `requirements.md` e o planejamento. Uma Issue `[Fase NN] Nome` pode ajudar na atribuição e nas notas, mas não é lock nem condição de conclusão.

Mantenha no máximo um PR aberto por branch e preserve PRs fechados no histórico. Um PR fechado sem merge mantém a fase `ACTIVE` e seus conflitos bloqueados; use `$finish-phase` para reabrir o PR ou, com decisão explícita do usuário, criar uma revisão substituta sem esconder o histórico anterior.

### Fluxo recomendado

#### 0. Criar ou atualizar as especificações globais

Execute `$manage-shared-specs` para o baseline, uma reorganização ampla ou uma decisão compartilhada. A mudança usa uma branch comum de documentação criada a partir da branch padrão remota e termina em PR. Fases não afetadas continuam trabalhando.

#### 1. Assumir e especificar uma fase

Execute `$start-phase`. A skill verifica dependências, conflitos, branches e PRs remotos, prepara `requirements.md`, `plan.md` e `validation.md`, e publica o commit de planejamento diretamente como uma nova ref `phase/NN-{slug}`. A criação falha se outro dev tiver criado a branch primeiro. Depois do push, ela confere os conflitos novamente; se duas fases conflitantes venceram a corrida em refs diferentes, nenhuma começa a implementação até os responsáveis escolherem qual claim prossegue.

Uma worktree separada ajuda quem mantém várias fases abertas, mas não é obrigatória. Para uma fase pequena, os três documentos podem ser breves, desde que objetivo, limites, ownership e validação estejam claros.

#### 2. Implementar

Use `$implement-phase` quando a entrega cruza frontend, API e backend. Use diretamente `$implement-frontend-phase`, `$implement-api-phase` ou `$implement-backend-phase` para uma frente isolada.

Dentro da fase, cada caminho tem um escritor por vez. Antes de publicar, atualize o estado remoto e confirme novamente dependências e conflitos. Se surgir uma decisão de stack ou roadmap:

- leve-a no PR da fase quando só aquela fase depende dela e nenhum trabalho separado precisa começar antes do merge;
- abra um PR curto de specs quando outra fase precisa da decisão ou quando uma fase de pré-requisito precisa entrar no roadmap antes;
- publique a fase de pré-requisito por esse PR de specs e registre a espera temporária quando o novo trabalho precisa terminar antes da fase ativa continuar;
- use uma fase de continuação quando o resultado ou gate original deixou de ser válido.

#### 3. Validar e abrir o PR

Execute `$finish-phase`. A skill roda os gates aplicáveis, registra evidências reais em `validation.md`, publica a branch e cria ou atualiza o PR. Um check não executado deve aparecer como `N/A` ou `Blocked`, nunca como aprovado.

O PR aberto representa `REVIEW`, não `DONE`. Merge remoto, limpeza de branch e remoção de worktree exigem autorização compatível com a ação.

#### 4. Revisar, integrar e reconciliar

Use `$deep-review <PR>` quando uma revisão multiagente for solicitada. Para emitir parecer de merge, a revisão precisa apontar para um commit publicado específico; mudanças não commitadas podem ser analisadas, mas não recebem parecer de merge.

Depois do merge, execute `$finish-phase` para confirmar validação, atualizar a branch padrão local e limpar apenas recursos locais seguros e autorizados. A fase passa a `DONE`, liberando suas dependentes.

#### 5. Atualizar o changelog

Execute `$changelog` quando as fases relevantes já estiverem integradas. O changelog usa uma branch comum de documentação e um PR próprio. Não exige branch fixa, lock ou Issue especial, e não publica tag, release ou deploy.

### Regras de coordenação

- Fases independentes podem avançar em paralelo quando dependências e conflitos permitem.
- Frontend, API e backend podem avançar em paralelo dentro da mesma fase quando os caminhos têm responsáveis distintos.
- Mudanças compartilhadas exigem comunicação, atualização da branch e resolução normal de conflitos do Git.
- Uma decisão urgente pausa somente o trabalho afetado. A aprovação vem do usuário, do líder designado ou de todos os responsáveis impactados.
- Não force-push, apague branch com trabalho único ou sobrescreva o arquivo de outro dev.
- Se uma branch já existir, coordene com o responsável em vez de criar um segundo claim.

### Sequência resumida

```text
$manage-shared-specs     baseline ou decisão global
          ↓
$start-phase             branch + planejamento
          ↓
$implement-phase         implementação por caminhos
          ↓
$finish-phase            validação + PR
          ↓
$deep-review             opcional, somente leitura
          ↓
merge autorizado
          ↓
$finish-phase            reconciliação
          ↓
$changelog               notas de release quando necessárias
```

### Skills auxiliares

| Skill | Uso |
| --- | --- |
| `$manage-shared-specs` | Criar ou atualizar missão, stack, roadmap e decisões compartilhadas. |
| `$start-phase` | Assumir uma fase elegível e publicar seu planejamento. |
| `$implement-phase` | Coordenar uma fase que cruza camadas. |
| `$finish-phase` | Validar, abrir ou atualizar o PR e reconciliar depois do merge. |
| `$deep-review` | Fazer revisão multiagente somente leitura quando solicitada. |
| `$changelog` | Preparar notas a partir de fases integradas e validadas. |
| `$library-skills` | Verificar e gerenciar skills fornecidas por pacotes. |
