# Deploy do Volta para o hackathon

O frontend Next.js roda na Vercel. O `render.yaml` provisiona o FastAPI e o
backend/core no mesmo Web Service e um PostgreSQL privado. O Blueprint usa os
planos Free do Render, portanto as evidências sintéticas ficam em armazenamento
efêmero e não sobrevivem a reinícios ou redeploys.

## 1. Publicar a API e o PostgreSQL no Render

1. No Render Dashboard, escolha **New > Blueprint** e conecte este repositório.
2. Confirme o arquivo `render.yaml` na raiz.
3. Durante a criação, preencha os valores marcados como secretos:
   - `CORS_ORIGINS`: inicialmente use o domínio de produção esperado da Vercel,
     no formato JSON `["https://SEU-PROJETO.vercel.app"]`;
   - `VOLTA_DEMO_BEARER_TOKEN`: gere uma senha aleatória longa, guarde-a no
     gerenciador de segredos e nunca a salve no repositório;
   - `OPENAI_API_KEY`: chave server-side usada pela extração e pelo Realtime.
4. Crie os recursos. O pre-deploy executa as migrações Alembic antes de iniciar
   o Uvicorn.
5. Aguarde `GET https://SEU-SERVICO.onrender.com/health` retornar
   `{"status":"ok"}`.

O serviço e o banco ficam em Virginia e se comunicam pela rede privada do
Render. O banco bloqueia conexões públicas. O Web Service usa uma única
instância porque o rate limit e as sessões de tempo real ainda possuem estado
local. No plano Free, o serviço pode hibernar após inatividade e o PostgreSQL
expira após 30 dias; use-o somente para a demonstração do hackathon.

## 2. Publicar o frontend na Vercel

1. Importe o mesmo repositório na Vercel.
2. Configure **Root Directory** como `frontend`.
3. Mantenha o framework detectado como **Next.js**. O `frontend/vercel.json`
   fixa os comandos de instalação e build.
4. Adicione as variáveis de Production:

   ```text
   NEXT_PUBLIC_API_BASE_URL=https://SEU-SERVICO.onrender.com
   NEXT_PUBLIC_INTAKE_USE_TEST_BOUNDARY=false
   ```

5. Publique e copie a URL canônica de produção.
6. Se a URL final diferir da informada inicialmente, atualize no Render:

   ```text
   CORS_ORIGINS=["https://SEU-PROJETO.vercel.app"]
   ```

   Em seguida, faça um redeploy da API.

## 3. Verificação após o deploy

1. Abra `/health` no Render e confirme HTTP 200.
2. Abra a URL da Vercel, informe o mesmo `VOLTA_DEMO_BEARER_TOKEN` na tela e
   execute Intake -> Mandate -> Sessions -> Comparison -> Evidence.
3. No navegador, confirme que as chamadas vão somente para o hostname Render,
   sem erros de CORS, HTTP 401 inesperado ou HTTP 5xx.
4. Teste criação e reprodução de evidência sintética durante a mesma execução
   do serviço. No plano Free, ela é apagada em um reinício ou redeploy.
5. Teste a credencial efêmera do OpenAI Realtime sem expor `OPENAI_API_KEY` ao
   navegador.

## Limite atual

O plano Free não oferece disco persistente. Antes de gravações reais, retenção
de evidências ou escala horizontal, substitua o adaptador de filesystem por
object storage privado com política explícita de expiração e exclusão e mova o
serviço para um plano pago. O produto ainda precisa das rotas finais de Twilio
Media Streams para afirmar que a telefonia P0.1 está publicada; o deploy atual
cobre a jornada web, texto e browser Realtime implementada no repositório.
