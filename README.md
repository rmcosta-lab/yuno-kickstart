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

## Pré-requisitos para trabalho paralelo

O fluxo de fases usa o GitHub como estado compartilhado. Antes de assumir uma fase, o ambiente precisa conseguir:

- ler o repositório e sua branch padrão remota;
- consultar, criar, atualizar, atribuir, fechar e reabrir Issues, além de consultar e criar branches e Pull Requests;
- identificar o responsável pela fase;
- criar uma Git ref com semântica **create-only**, que falha se a branch já existir;
- apagar somente refs de mutex ou branches-lock com compare-and-delete sobre o SHA esperado, depois da confirmação prevista pela skill;
- manter as refs de coordenação fora de uma proteção que impeça sua liberação autorizada.

O servidor oficial do Model Context Protocol (MCP) para GitHub deve estar habilitado e autenticado, conforme `AGENTS.md`. Um cliente autenticado equivalente só é válido quando preserva as mesmas garantias. Sem acesso remoto compartilhado, `$start-phase` interrompe o fluxo: uma branch apenas local não reserva uma fase para a equipe.

## Como o roadmap define as fases

`docs/project-specs/roadmap.md` é um grafo estático, não uma fila numérica nem um quadro de status. As fases representam resultados ou slices verticais; frontend, API e backend são workstreams dentro delas, não três roadmaps separados. Cada fase declara:

```markdown
### Fase 04 — Resultado da fase

Slug: resultado-da-fase
Depends on: 02
Conflicts with: none
Gate: evidência observável mínima para enviar a fase à revisão
```

- `Slug` é canônico, usa letras ASCII minúsculas, números e hífens, e deve corresponder a `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- `Depends on` contém somente pré-requisitos reais.
- `Conflicts with` contém fases que não podem ficar ativas simultaneamente, inclusive quando disputam um arquivo global ou uma decisão serializada.
- Use `none` explicitamente quando a lista estiver vazia.
- O número identifica a fase, mas não cria dependência implícita.
- Não acrescente `✅`, responsável, branch ou estado dinâmico ao roadmap.

Depois que uma fase tiver qualquer Issue, branch, planejamento publicado ou PR, seu número, nome, slug, dependências, conflitos e gate ficam imutáveis. Uma mudança de resultado deve virar uma nova fase; reescrever a identidade antiga criaria `DRIFT` e poderia esconder o histórico usado para calcular `DONE`.

Todo conflito vale nos dois sentidos, mesmo quando aparece em uma única seção. Uma fase em `DRIFT` também mantém o conflito bloqueado até a reconciliação.

Assim, se a Fase 04 depender apenas da Fase 02, ela poderá ser iniciada logo após a Fase 02 terminar, mesmo que as Fases 01 e 03 continuem em andamento, desde que nenhuma delas tenha conflito com a Fase 04.

### Arquivos de especificação

O diretório `docs/project-specs/` ainda será criado. As referências abaixo são intencionais e devem ser preservadas:

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

Enquanto o roadmap não existir, `$start-phase` interrompe com o diagnóstico do pré-requisito. Use `$manage-shared-specs` para criar o baseline antes da primeira fase.

Esses três arquivos são globais e ficam somente leitura durante fases paralelas. Toda alteração passa pela tarefa serializada `$manage-shared-specs`.

## Estado compartilhado de uma fase

Cada fase usa:

- uma Issue canônica: `[Fase NN] Nome`;
- uma branch remota determinística: `phase/NN-{slug}`, usando o campo estático `Slug` do roadmap;
- um pull request (PR) dessa branch para a branch padrão remota.

O redutor verifica `DRIFT` antes dos demais estados. Depois, deriva o estado destes fatos:

| Estado | Significado |
| --- | --- |
| `DRIFT` | Issue, branch, owner, planning commit, spec e PR discordam, estão duplicados ou incluem PR fechado sem merge. |
| `DONE` | Checks e validação da fase aceitos + PR integrado na branch padrão remota + Issue fechada. |
| `CANCELED` | Fase vazia retirada explicitamente, sem planning, PR ou trabalho único; nunca satisfaz uma dependência. |
| `REVIEW` | Issue e planning publicados + exatamente um PR aberto para a branch padrão. |
| `IN_PROGRESS` | Issue aberta e atribuída + branch remota contendo o planning commit e a spec publicados + nenhum PR dessa tentativa. |
| `BLOCKED` | Fase ainda não assumida, com dependência pendente ou conflito declarado ativo. |
| `READY` | Fase ainda não assumida, com dependências concluídas, nenhum conflito ativo e nenhum claim remoto. |

Labels e GitHub Projects podem espelhar esses estados, mas não são necessários para a correção do fluxo. A branch remota da fase é o claim durável porque sua criação pode ser atômica; assignee e label não são locks.

Um mutex remoto curto, `coordination/phase-claim-lock`, serializa claims, publicação de planning, reparos, bloqueio de merge durante follow-up, publicação das tarefas fixas e mutações remotas de `$finish-phase`. Isso impede corridas entre fases, reviews e mudanças globais. A skill cria e libera esse mutex dentro de uma transação curta; validações longas e cleanup local ficam fora dela. Se uma execução parar no meio, ninguém remove o mutex por idade: um responsável deve reconciliá-lo depois de confirmar que nenhum `$start-phase`, `$manage-shared-specs`, `$implement-phase`, implementador direto de camada, `$changelog` ou `$finish-phase` está usando a ref.

## Fluxo recomendado

### 0. Criar ou atualizar as especificações globais

Antes da primeira fase, ou quando missão, stack, roadmap ou challenge plan precisarem mudar:

```text
$manage-shared-specs
```

A branch-lock continua sendo `docs/project-specs`. Ela é diferente do diretório `docs/project-specs/`, apesar do nome igual.

A skill cria ou atualiza somente estes arquivos globais:

- `docs/project-specs/mission.md`
- `docs/project-specs/tech-stack.md`
- `docs/project-specs/roadmap.md`
- `docs/decisions/challenge-plan.md`

Depois, ela abre um PR e para em review. A alteração bloqueia enquanto houver fase em `IN_PROGRESS`, `REVIEW` ou `DRIFT`.

Depois do merge, execute `$manage-shared-specs` novamente para verificar o conteúdo integrado e liberar a branch-lock. Nenhuma fase pode bootstrapar o próprio roadmap.

### 1. Assumir e especificar uma fase elegível

Na worktree principal, execute:

```text
$start-phase
```

A skill executa estas etapas:

1. lê o grafo e reconstrói o estado remoto de todas as fases;
2. escolhe a fase elegível de menor número, ou valida uma fase indicada pelo usuário;
3. pede autorização para criar e liberar o mutex e para publicar o claim;
4. cria o mutex com uma operação create-only;
5. relê toda a elegibilidade enquanto mantém o mutex;
6. cria uma única vez a branch remota `phase/NN-{slug}` no hash (SHA) atual da branch padrão;
7. cria, reutiliza ou reabre a única Issue canônica, registra um novo attempt e a atribui ao login GitHub autenticado;
8. libera o mutex somente depois que branch, Issue, attempt e owner estiverem consistentes;
9. cria a worktree local;
10. escreve `requirements.md`, `plan.md` e `validation.md` em `docs/project-specs/YYYY-MM-DD-NN-{slug}/`;
11. publica o commit `Start Fase NN: Nome` e registra seu SHA na Issue.

Se outro dev vencer a corrida, a criação da ref falha e a skill atualiza o estado antes de continuar. Ela não escolhe silenciosamente outra fase. Se o claim remoto for criado, mas uma etapa posterior falhar, a branch permanece reservada como claim incompleto; ninguém deve apagá-la automaticamente.

### 2. Implementar uma fase que cruza camadas

Dentro da worktree criada:

```text
$implement-phase
```

Essa skill valida Issue, owner e branch remota antes de trabalhar. Depois congela dois contratos:

- contrato HTTP: Pydantic → OpenAPI → Orval;
- contrato de aplicação: API → serviços tipados do backend/core.

Ela coordena as frentes necessárias em paralelo, com responsabilidade exclusiva:

- frontend escreve em `frontend/**`;
- API/BFF escreve em `api/**`;
- backend/core escreve em `backend/**`;
- a coordenadora escreve no diretório da spec da fase e nos caminhos compartilhados exatos que `plan.md` atribuir com exclusividade.

Os três arquivos globais em `docs/project-specs/` ficam somente leitura durante uma fase. O mesmo vale para a documentação global, o README, o AGENTS e as configurações raiz.

O coordenador escreve somente no diretório datado da fase ativa. Se outra fase puder escrever o mesmo caminho, declare o conflito no roadmap ou adie a mudança para uma tarefa serializada.

### 3. Implementar somente uma camada

Para uma tarefa realmente isolada, use diretamente:

```text
$implement-frontend-phase
$implement-api-phase
$implement-backend-phase
```

- `$implement-frontend-phase`: Next.js, integração Orval e validação no navegador.
- `$implement-api-phase`: FastAPI, Pydantic e OpenAPI, sem regras de negócio nos routers.
- `$implement-backend-phase`: domínio, serviços, repositórios, persistência e adapters, sem depender de FastAPI.

Quando `$implement-phase` coordena a fase, ela própria aciona somente os workstreams necessários. Não execute outra skill concorrente sobre os mesmos arquivos. Quando uma skill de camada é invocada diretamente, ela também exige um claim remoto consistente.

### 4. Validar e enviar para revisão

Quando a implementação e os gates estiverem completos:

```text
$finish-phase
```

No modo normal, a skill:

1. revalida os checks aplicáveis;
2. consolida a evidência em `validation.md`;
3. cria o commit `Complete Fase NN: Nome`;
4. envia somente a branch da fase;
5. cria ou atualiza o PR canônico com a referência `Closes #123` para a Issue correspondente.

O resultado desse passo é `REVIEW`, não `DONE`. A skill não faz merge local em `main`, não fecha a Issue antecipadamente e não apaga a worktree.

### 5. Revisar o SHA publicado

Execute a revisão sobre o PR:

```text
$deep-review 123
```

A revisão é somente leitura, confere arquitetura, segurança/pagamentos, experiência de demonstração e consistência do claim. O parecer vale para o SHA exato informado; um novo commit exige revisão do intervalo alterado.

### 6. Integrar e reconciliar

O PR pode ser integrado por um responsável humano ou por `$finish-phase` somente quando o usuário pedir explicitamente o merge remoto e todos os checks e approvals exigidos estiverem satisfeitos.

Depois do merge, execute novamente:

```text
$finish-phase
```

Agora a skill entra em modo de reconciliação:

- confirma o PR integrado na branch padrão;
- confirma ou corrige o fechamento da Issue;
- recalcula quais fases ficaram `READY`;
- atualiza a branch padrão local com fast-forward;
- remove apenas a worktree e a branch local que puderem ser removidas com segurança.

A branch remota nunca é apagada sem pedido explícito.

### 7. Atualizar notas de release

`CHANGELOG.md` pertence exclusivamente a `$changelog` e nunca deve ser alterado por uma branch de fase. Depois que as fases relevantes forem integradas, inicie a tarefa serializada:

```text
$changelog
```

A skill usa a branch fixa `docs/changelog` como lock create-only, lê apenas PRs integrados e evidências validadas, cria o commit e abre um PR de documentação. O modo normal para em review. Depois do merge, execute `$changelog` novamente para verificar o resultado e liberar a branch-lock.

Ela não publica tag, GitHub Release ou deploy.

## Dois níveis de paralelismo

O projeto admite dois tipos de paralelismo ao mesmo tempo:

1. **Entre fases:** vários devs trabalham em fases diferentes quando a elegibilidade calculada de roadmap + GitHub estiver `READY` imediatamente antes do claim. Depois que a ref é criada, a fase sai de `READY`; torna-se `IN_PROGRESS` somente quando Issue, owner, planning commit e spec publicados estiverem consistentes.
2. **Dentro de uma fase:** frontend, API e backend trabalham em paralelo sob `$implement-phase`, depois que os contratos estão congelados.

Esses níveis não devem ser confundidos. Uma fase bloqueada por dependência não pode ser iniciada só porque existe um dev livre; uma camada independente dentro de uma fase já assumida pode.

## Recuperação de inconsistências

Se aparecer branch sem Issue, Issue atribuída sem branch, PR duplicado, PR fechado sem merge ou histórico divergente, a fase fica `DRIFT`. O fluxo para e relata os fatos.

Um PR fechado sem merge só volta ao fluxo quando `$finish-phase` reabre aquele mesmo PR, após restaurar e revalidar seu head. A skill nunca cria um PR substituto para esconder o histórico; se a política do repositório impedir a reabertura, o claim permanece preservado e bloqueado até a restrição ser resolvida.

Não libere um claim por timeout e não apague automaticamente uma branch com trabalho possivelmente único. Um responsável deve reconciliar, transferir ou liberar o claim explicitamente depois de inspecionar commits e PRs. Retomar um claim incompleto exige confirmação explícita do owner ou de um handoff e usa o mutex global durante a releitura e o reparo da Issue; possuir um checkout local não prova ownership.

Uma tentativa de fase comprovadamente vazia pode ser fechada como `ABANDONED`, sem assignee, e depois reclamada pela mesma Issue com novo attempt. Se o resultado deixou de fazer sentido, ela pode ser fechada como `CANCELED`; essa identidade não volta à seleção e não satisfaz dependências. Uma substituição usa novo número de fase.

Se uma edição externa alterar somente os campos congelados de uma fase, `$manage-shared-specs` pode entrar no modo explícito de restauração, inclusive para destravar uma fase ativa ou em review depois que seu trabalho for pausado. Ele recompõe apenas os valores históricos quando Issue, planejamento, branch e PR concordam; qualquer ambiguidade ou mudança de produto continua bloqueada. Um PR já integrado com sua única Issue ainda aberta também pode aguardar essa restauração e ser reconciliado depois por `$finish-phase`.

Quando uma tarefa vazia de specs ou changelog for explicitamente abandonada, sua Issue canônica é fechada com `Outcome: ABANDONED`. Se a branch padrão continuar no mesmo SHA, a próxima tentativa reabre essa única Issue, registra um novo `Current attempt` e preserva o histórico; ela nunca cria outra Issue com o mesmo título.

## Sequência resumida

```text
$manage-shared-specs
      │ baseline global integrado
      ▼
$start-phase
      │ claim atômico + planejamento publicado
      ▼
$implement-phase
      ├── $implement-frontend-phase
      ├── $implement-api-phase
      └── $implement-backend-phase
      ▼
$finish-phase
      │ push + PR
      ▼
$deep-review 123
      │ merge autorizado/humano
      ▼
$finish-phase
      │ reconciliação + novas fases READY
      ▼
$changelog
      │ PR de documentação
      ▼
$changelog
      reconciliação da branch-lock
```

## Skills auxiliares

| Skill | Uso |
| --- | --- |
| `$manage-shared-specs` | Publica e reconcilia missão, stack, roadmap e challenge plan pela branch-lock `docs/project-specs`. |
| `$deep-review` | Revisão multiagente, somente leitura, vinculada ao SHA de uma branch ou PR. |
| `$changelog` | Publica e reconcilia `CHANGELOG.md` pela branch-lock fixa `docs/changelog`. |
| `$library-skills` | Descobre, instala, atualiza ou verifica skills provenientes da Library Skills. |
