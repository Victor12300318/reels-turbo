# 📌 CHECKPOINT DO PROJETO: Clonify AI

**Data da Atualização:** 25 de Julho de 2026  
**Último Commit:** `6243d87` na branch `main` (`origin/main`)  
**Status do Projeto:** Estável (50/50 testes passando no `pytest`)

---

## 🎯 Visão Geral do Projeto
O **Clonify AI** (anteriormente chamado *Reels Cloner MVP*) é um SaaS de automação para Instagram Reels. Ele baixa Reels do Instagram, encontra o melhor vídeo correspondente em uma biblioteca local (ou S3) usando Visão Computacional / IA, aplica sobreposições de texto que evitam rostos (FFmpeg), permite agendamento e publica automaticamente através da Meta Graph API.

---

## 🛠️ Tecnologias & Arquitetura
- **Backend:** Python 3.11+ / FastAPI (`src/app.py`), SQLite (`data/videos.db`), FFmpeg, `yt-dlp`.
- **Frontend:** Next.js (TypeScript, Tailwind CSS, Lucide React icons, `Plus Jakarta Sans`).
- **Design System:** Clean Light SaaS estilo ManyChat (`#F8FAFC`, `#FFFFFF`, `#0066FF`), zero emojis no código/UI, ícones vetoriais SVG, layout responsivo com menu lateral expansível/recolhível.
- **Provedores de IA Integrados:** 
  - **Google Gemini** (`google-genai` / `gemini-3.5-flash`).
  - **OpenRouter REST API** (suportando DeepSeek, GPT-4o, Claude 3.5, etc.).
  - Alternância e chave de API gerenciadas no painel do Administrador via tabela `system_settings` no SQLite.

---

## 🚀 Funcionalidades Recentes Implementadas

1. **Rebranding Completo para Clonify AI:**
   - Todo o frontend (`app/page.tsx`, `layout.tsx`, `terms`, `privacy`, `data-deletion`) e backend (`app.py`, `scheduler.py`, `main.py`) utilizam o nome e as legendas padrão do **Clonify AI**.

2. **Arquitetura Multi-Provedor de IA (`src/ai_client.py`):**
   - Factory unificada `get_ai_client()` que consulta as configurações do sistema (`system_settings`) e utiliza `OpenRouterClient` ou `GeminiClient` de forma transparente no analisador e matcher.
   - Formulário de configuração no Painel de Admin (`frontend/components/UserManagementTab.tsx`).

3. **Gerenciamento Completo de Agendamento:**
   - Popup Modal interativo no Feed para editar data/hora do agendamento (`PATCH /api/v1/jobs/{job_id}/schedule`).
   - Botão para cancelar agendamento (`DELETE /api/v1/jobs/{job_id}/schedule`), retornando o status do vídeo para `'completed'` (Pronto para Postar).
   - **Avanço Automático da Fila ao Postar Antecipadamente:** Se um vídeo agendado (ex: 11h) for publicado antes do prazo via "Postar Agora", ele é marcado como postado (`posted_at` preenchido, `scheduled_at = NULL`). Os vídeos agendados subsequentes na fila do usuário avançam automaticamente 1 slot (ex: o vídeo das 15h assume o slot das 11h), garantindo que no horário agendado (11h) o próximo vídeo seja publicado sem duplicar postagens.

4. **Otimizações no Feed e UI:**
   - **Performance:** Renderização *lazy* dos players de vídeo embutidos (carrega o `<video>` apenas ao clicar no thumbnail) e paginação ("Carregar mais vídeos", 6 por página).
   - **Feedback de Publicação:** Estado de carregamento individual no botão "Postar Agora" para evitar múltiplos cliques.
   - **Tratamento Safari/iOS:** Proteção contra exceções de `new Notification()` em navegadores móveis sem suporte completo a notificações web.
   - **Badges de Status:** Distinção visual clara entre *Postado* (Data de postagem), *Agendado* (Data/hora futura) e *Pronto para Postar*.

---

## 📂 Arquivos Chave da Aplicação

- `src/ai_client.py`: Factory e clientes de IA (Gemini e OpenRouter).
- `src/app.py`: Endpoints da API FastAPI (Auth, Jobs, Schedule, Admin Settings, Post).
- `src/database.py`: Repositório SQLite (`system_settings`, `jobs`, `users`, `videos`).
- `src/scheduler.py`: Daemon de postagem automática de Reels agendados.
- `frontend/app/page.tsx`: Dashboard principal (Feed, Modal de Agendamento, Sidebar responsiva).
- `frontend/components/UserManagementTab.tsx`: Painel Admin com gestão de usuários e provedor de IA.
- `docs/superpowers/specs/2026-07-25-clonify-ai-design.md`: Especificação técnica de design.
- `docs/superpowers/plans/2026-07-25-clonify-ai-plan.md`: Plano de execução concluído.

---

## ⚡ Comandos Principais para a Próxima Sessão

- **Executar Testes do Backend:**
  ```bash
  pytest
  ```

- **Indexar Vídeos Locais:**
  ```bash
  python -m src.main index
  ```

- **Iniciar Backend FastAPI (Dev):**
  ```bash
  uvicorn src.app:app --reload
  ```

- **Iniciar Frontend Next.js (Dev):**
  ```bash
  cd frontend && npm run dev
  ```

- **Habilidades Úteis para o Agente Invocar:**
  - `systematic-debugging`: Para investigar bugs ou erros na execução da pipeline.
  - `code-review`: Para revisar alterações antes de novos merges.
