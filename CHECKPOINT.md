# 📌 CHECKPOINT DO PROJETO: Clonify AI

**Data da Atualização:** 25 de Julho de 2026  
**Último Commit:** `6243d87` na branch `main` (`origin/main`)  
**Status do Projeto:** Estável (57/57 testes passando no `pytest`)

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

5. **Proteção Rigorosa Contra Sobreposição de Texto em Rostos (`src/video_processor.py` & `src/analyzer.py`):**
   - **Zona Segura Forçada:** Sempre que um rosto/pessoa for detectado no vídeo (padrão em vídeos selfie/talking-head), a posição do texto é forçada para a zona inferior limpa (área do peito/torso, $y = 62\% \to 79\%$).
   - **Quebra de Linhas Responsiva:** Texto formatado com no máximo 26 caracteres por linha e restrição de largura a $78\%$ da tela para manter margens laterais limpas longe dos botões de ação do Instagram (curtir/comentar/compartilhar).
   - **Eliminação de Texto Central/Superior sobre Rostos:** Impede que o texto cubra olhos, boca, nariz ou testa (evitando o problema visto nas imagens de exemplo).

6. **Prévias e Players de Vídeo em Modal Popup (Biblioteca + Clonador):**
   - Exibição de thumbnails/capas reais em cada card da biblioteca de vídeos.
   - Modal Popup com player `<video>` para assistir a qualquer vídeo local original ou Reels de referência.

7. **Algoritmo Anti-Repetição da Biblioteca (`src/matcher.py` & `src/database.py`):**
   - Rastreamento de `usage_count` e `last_used_at` na tabela `videos`.
   - Bônus de +20% no ranking para vídeos nunca usados (`usage_count = 0`) e penalidade progressiva por frequência e recência.

8. **Janela de Agendamento Segura (06:00 às 21:00 UTC-3) (`src/scheduler.py`):**
   - Bloqueio automático de agendamentos de madrugada. Qualquer horário entre 21:01 e 05:59 é ajustado para 06:00 AM.

9. **Engine RAG com Gemini Embeddings + Meta Graph API Insights (`src/ai_client.py` & `src/instagram_publisher.py`):**
   - Captura do `instagram_media_id` ao publicar.
   - Coleta de métricas (`views`, `likes`, `comments`, `shares`, `reach`) via Meta Graph API `/insights`.
   - Injeção das métricas dos Top 5 Reels no prompt da IA (Gemini/OpenRouter) para aprendizado e geração contínua de alto engajamento.

10. **Modo Fila Sequencial, Crop 9:16 Re-encoded & Arquivamento de Jobs (`src/app.py` & `src/video_processor.py`):**
    - **Modo Fila (1 por vez):** Processamento sequencial FIFO (`job_processing_queue`) de clonagem para evitar sobrecarga de CPU/RAM, glitches visuais e falhas ao enviar múltiplos Reels.
    - **Renderização Limpa 1080x1920 9:16:** Recodificação libx264 obrigatória em `adjust_duration` com crop `scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920`, eliminando barras pretas e artefatos de vídeo (glitches).
    - **Arquivamento e Remoção do Feed:** Suporte a `status = 'archived'` (`DELETE /api/v1/jobs/{job_id}`) com remoção imediata da tela do usuário ao cancelar ou arquivar.

11. **Login Direto com o Instagram Business OAuth & Docker Compose Sync (`src/app.py`, `src/config.py`, `docker-compose.yml`):**
    - **Leitura estrita via `.env`:** Removidos IDs hardcodados do código. Todas as chaves (`META_APP_ID`, `META_APP_SECRET`, `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET`, `INSTAGRAM_REDIRECT_URI`) são lidas diretamente das variáveis de ambiente.
    - **Docker Compose:** Repassadas todas as novas variáveis para o contêiner `reels-api` via `.env`.
    - **Direto pelo Instagram:** Redirecionamento OAuth alterado para `https://www.instagram.com/oauth/authorize` com suporte a `INSTAGRAM_CLIENT_ID` e fallback automático para Meta App ID.

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
