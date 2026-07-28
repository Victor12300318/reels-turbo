# 📐 ESPECIFICAÇÃO DE DESIGN TÉCNICO: Clonify AI
**Funcionalidades:** Prévias em Vídeo, Algoritmo Anti-Repetição da Biblioteca, Janela de Agendamento Segura (Sem Horários Mortos) & Engine RAG com Gemini Embeddings + Meta Graph API Insights  
**Data:** 25 de Julho de 2026  
**Status:** Aprovado pelo Usuário  

---

## 1. Visão Geral do Sistema

O objetivo desta especificação é evoluir o **Clonify AI** para uma plataforma inteligente de automação de vídeo com aprendizado contínuo, melhor visualização de assets e otimização de horários de publicação.

A solução cobre 4 pilares principais:
1. **Prévias e Players em Vídeo:** Visualização com thumbnails e players embutidos na aba **Biblioteca** e na aba **Clonador (Feed de Jobs)**.
2. **Algoritmo Anti-Repetição da Biblioteca:** Rotação inteligente ponderada por recência e frequência para garantir circulação uniforme de todos os 30+ vídeos da biblioteca.
3. **Janela de Agendamento Segura (06:00h às 21:00h):** Bloqueio automático de postagens em horários mortos de madrugada, ajustando slots fora da janela para o início da próxima janela útil (06:00 AM).
4. **Engine RAG (Gemini Embeddings + Meta Graph API):** Sincronização periódica e sob demanda de métricas de engajamento do Instagram (`views`, `likes`, `comments`, `shares`, `reach`), geração de embeddings vetoriais via `text-embedding-004` (Gemini API) e injeção do histórico dos Top 5 Reels mais performáticos no prompt da IA para aumentar a assertividade das novas gerações.

---

## 2. Detalhamento dos Módulos

### 2.1. Prévias & Players em Vídeo (Biblioteca + Aba Clonador)

#### Backend (`src/app.py`)
- `GET /api/v1/videos/{video_id}/thumbnail`: Retorna o arquivo de imagem JPG/PNG do primeiro frame do vídeo da biblioteca (`frame_paths[0]`).
- `GET /api/v1/videos/{video_id}/stream`: Endpoint de streaming de mídia (`FileResponse` com suporte a range de bytes) do vídeo local original para reprodução no player web.

#### Frontend (`frontend/app/page.tsx`)
- **Aba Biblioteca:**
  - Exibe um card visual com thumbnail extraído do vídeo.
  - Exibe contadores e badges: `Usado X vezes` (badge verde se 0 usos) e `Último uso: DD/MM/AAAA`.
  - Ao clicar no thumbnail, abre um **Modal Popup com Player `<video>`** para assistir ao vídeo local original em alta definição.
- **Aba Clonador (Feed de Jobs):**
  - Adiciona botões com thumbnail para prévia em vídeo tanto do **Vídeo de Referência** (baixado do Instagram) quanto do **Vídeo Local Escolhido**.

---

### 2.2. Algoritmo Anti-Repetição da Biblioteca (Frequência & Recência)

#### Banco de Dados (`src/database.py`)
- Colunas na tabela `videos` (compatível com SQLite e PostgreSQL):
  - `usage_count` (`INTEGER DEFAULT 0`): total de vezes que o vídeo foi selecionado para clonagem.
  - `last_used_at` (`TEXT`): ISO timestamp da última seleção.
- Método `repo.increment_video_usage(video_id: str)`: incrementa `usage_count` e define `last_used_at = now()`.

#### Rotação Ponderada no Matcher (`src/matcher.py`)
- O `Matcher` avalia o ranking de afinidade visual/temática via IA (Score Base: $0 \to 100$).
- Aplica fórmula de pontuação ajustada:
  - **Bônus para vídeos nunca usados (`usage_count = 0`):** +20 pontos.
  - **Penalidade por Recência:** Se usado nos últimos 7 dias, penalização de $-(30 \times (7 - \text{dias}) / 7)$ pontos.
  - **Penalidade por Frequência:** $-5 \times usage\_count$ pontos.
- Garante rotação uniforme de toda a biblioteca de vídeos antes do reuso.

---

### 2.3. Janela de Agendamento Segura (06:00h às 21:00h - UTC-3)

#### Módulo Scheduler (`src/scheduler.py`)
- Função `adjust_to_safe_posting_window(dt: datetime, timezone_offset_hours: int = -3) -> datetime`:
  - Converte a data/hora para o fuso horário local (padrão Horário de Brasília / UTC-3).
  - Se a hora estiver entre `21:01` e `05:59`:
    - Ajusta a hora para `06:00` do mesmo dia (se for antes das 06:00) ou `06:00` do dia seguinte (se for após as 21:00).
- Ajuste nas funções de agendamento em lote (`calculate_batch_timestamps`) e na fila dinâmica de agendamento em `src/app.py`.

---

### 2.4. Engine RAG: Gemini Embeddings + Meta Graph API Insights

#### Banco de Dados (`src/database.py`)
- Coluna `instagram_media_id` (`TEXT UNIQUE`) na tabela `jobs`.
- Coluna `embedding` (`TEXT`) na tabela `jobs` para armazenar o vetor numérico (768 dimensões) gerado por `text-embedding-004`.
- Tabela `media_insights`:
  - `id` (PRIMARY KEY)
  - `job_id` (TEXT, FK jobs.id)
  - `instagram_media_id` (TEXT UNIQUE)
  - `views` (INTEGER DEFAULT 0)
  - `likes` (INTEGER DEFAULT 0)
  - `comments` (INTEGER DEFAULT 0)
  - `shares` (INTEGER DEFAULT 0)
  - `reach` (INTEGER DEFAULT 0)
  - `engagement_score` (REAL DEFAULT 0.0)
  - `synced_at` (TEXT)

#### Integração Meta Graph API (`src/instagram_publisher.py` & `src/scheduler.py`)
- Ao publicar um Reels no Instagram, o `instagram_media_id` é capturado do retorno da API e salvo no banco de dados.
- Função `sync_meta_insights(repo)`:
  - Consulta a Meta Graph API no endpoint `GET /v19.0/{media_id}/insights?metric=plays,likes,comments,shares,reach`.
  - Atualiza as métricas na tabela `media_insights` e calcula o `engagement_score = views + (likes * 3) + (comments * 5) + (shares * 7)`.
- **Sincronização Híbrida:**
  - **Daemon Automático:** Cron rodando em background a cada 6 horas (`process_due_scheduled_jobs` / background task).
  - **Botão Manual:** Endpoint `POST /api/v1/insights/sync` + Botão *"Sincronizar Métricas Meta"* no painel do usuário.

#### Motor RAG & Injeção no Agente de IA (`src/ai_client.py` & `src/matcher.py`)
- Método `get_embedding(text: str)` em `GeminiClient` utilizando o modelo `text-embedding-004`.
- Função `get_top_performing_reels_context(repo, user_id: str, top_k: int = 5) -> str`:
  - Recupera os 5 Reels do usuário com maior `engagement_score`.
  - Monta um resumo contextual (Hook, legenda, tema do vídeo original e views/likes atingidos).
- Injeção em `Matcher.rank_candidates` e `Analyzer.analyze_text_style`:
  - O prompt recebe a instrução da **Memória RAG**:
    > *"MEMÓRIA DE ALTO ENGAJAMENTO DO USUÁRIO:*
    > *Os vídeos do usuário com melhor desempenho e retenção possuem os seguintes padrões:*
    > *1. [Métricas: 12.500 views, 850 likes] Gancho: 'Quando ela acha que...', Legenda: '...', Tema: polo azul.*
    > *Dê preferência a combinações e formatos que espelhem a estrutura desses Reels de alto engajamento."*

---

## 3. Testes & Verificação

1. **Testes do Algoritmo Anti-Repetição:**
   - `test_video_usage_increment_and_penalty()` em `tests/test_matcher.py` e `tests/test_database.py`.
2. **Testes da Janela Segura:**
   - `test_safe_posting_window_adjustment()` em `tests/test_scheduler.py` garantindo ajuste automático de horários das 02:00 AM para 06:00 AM.
3. **Testes do RAG & Meta Insights:**
   - `test_meta_insights_sync()` em `tests/test_instagram_publisher.py`.
   - `test_gemini_embedding_and_rag_context()` em `tests/test_ai_client.py`.
4. **Verificação Completa de Regressão:**
   - Execução de `pytest` garantindo 100% de aprovação de todos os testes existentes e novos.

---

## 4. Próximos Passos
Após aprovação desta especificação pelo usuário, o plano de implementação detalhado será gerado via `writing-plans`.
