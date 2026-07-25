# Especificação de Design — Reels Cloner MVP (1ª Iteração)

**Data:** 2026-07-18  
**Status:** Aprovado para implementação  
**Proprietário:** victor.felix  

---

## 1. Contexto e Objetivo

Construir um MVP em Python 3.11+ que, a partir de uma URL de um Reels do Instagram, baixe o vídeo de referência, compare-o com os vídeos locais do usuário e gere um novo vídeo curto que:

1. copia a música/áudio do Reels de referência;
2. usa um dos vídeos locais como base visual;
3. aplica o texto extraído do Reels em uma posição que não cubra o rosto do usuário.

A interface da 1ª iteração será uma **CLI simples**; a integração com WhatsApp (Wuzapi) ficará para iterações futuras.

---

## 2. Escopo da 1ª Iteração

### Dentro do escopo

- Baixar vídeo de referência de uma URL do Instagram via `yt-dlp`.
- Indexar automaticamente uma pasta local de vídeos (`C:\Users\victor.felix\Pictures\reels-turbo\Vídeos do fuga`) usando o Gemini 2.0 Flash.
- Persistir metadados dos vídeos locais em SQLite.
- Comparar o vídeo de referência com os vídeos locais e escolher automaticamente o mais adequado (abordagem híbrida: ranqueamento textual + decisão multimodal com os 3 melhores candidatos).
- Extrair áudio do vídeo de referência.
- Ajustar o vídeo local escolhido para ter a mesma duração do áudio (`loop` se for mais curto; `trim` se for mais longo).
- Extrair texto na tela do Reels com OCR visual via Gemini.
- Detectar a posição do rosto no vídeo local escolhido via Gemini.
- Posicionar o texto extraído na região oposta ao rosto (topo/base) usando FFmpeg `drawtext`.
- Entregar o vídeo final em `data/output/`.

### Fora do escopo

- Integração com Wuzapi/WhatsApp.
- Interface web ou API REST.
- Sincronização de legendas por timestamp (o texto será aplicado como overlay estático no vídeo final).
- Múltiplos templates ou animações de texto.

---

## 3. Requisitos Funcionais

| ID | Descrição |
|----|-----------|
| RF01 | O sistema deve aceitar uma URL do Instagram Reels pela CLI. |
| RF02 | O sistema deve baixar o vídeo de referência e salvá-lo localmente. |
| RF03 | O sistema deve extrair frames representativos (início, meio, fim) de um vídeo. |
| RF04 | O sistema deve gerar uma descrição textual rica de cada vídeo local usando Gemini. |
| RF05 | O sistema deve salvar metadados e descrições em SQLite. |
| RF06 | O sistema deve reindexar vídeos novos sem perder dados antigos. |
| RF07 | O sistema deve ranquear vídeos locais contra o vídeo de referência usando descrições textuais. |
| RF08 | O sistema deve selecionar o melhor vídeo local usando frames dos 3 melhores candidatos + frames do Reels. |
| RF09 | O sistema deve extrair o texto visível na tela do Reels. |
| RF10 | O sistema deve ajustar a duração do vídeo local à duração do áudio do Reels. |
| RF11 | O sistema deve detectar a posição aproximada do rosto no vídeo local. |
| RF12 | O sistema deve renderizar o vídeo final com áudio do Reels e texto posicionado dinamicamente. |

---

## 4. Arquitetura e Componentes

```text
src/
├── __init__.py
├── main.py              # CLI principal (comandos index e clone)
├── config.py            # Configurações e variáveis de ambiente
├── database.py          # Acesso ao SQLite (tabelas videos, jobs)
├── indexer.py           # Análise e indexação dos vídeos locais
├── downloader.py        # Download de Reels com yt-dlp
├── analyzer.py          # Extração de frames, descrição e texto com Gemini
├── matcher.py           # Ranqueamento e seleção do vídeo local
├── video_processor.py   # Manipulação de vídeo/áudio com FFmpeg
└── gemini_client.py     # Cliente unificado para chamadas ao Gemini
```

### Responsabilidades

- **`main.py`**: pontos de entrada `index` e `clone <url>`; orquestra os demais módulos.
- **`config.py`**: centraliza `GEMINI_API_KEY`, `LOCAL_VIDEOS_DIR`, `DATA_DIR`, `GEMINI_MODEL`, `FRAMES_PER_VIDEO`, etc.
- **`database.py`**: schema, inserção/atualização e consulta de metadados no SQLite.
- **`indexer.py`**: itera sobre os vídeos da pasta local, extrai frames e chama `analyzer` para gerar descrição; persiste no banco.
- **`downloader.py`**: baixa o Reels com `yt-dlp` e retorna o caminho local.
- **`analyzer.py`**: funções para (a) descrever vídeo a partir de frames; (b) extrair texto na tela; (c) detectar posição do rosto.
- **`matcher.py`**: lê metadados locais, ranqueia contra a descrição do Reels; depois faz a escolha multimodal final.
- **`video_processor.py`**: executa `ffmpeg` para extrair áudio, loop/trim, renderizar vídeo com `drawtext`.
- **`gemini_client.py`**: encapsula autenticação, upload de imagens e chamadas ao modelo.

---

## 5. Fluxo de Dados

### Comando `index`

1. Localiza todos os arquivos `.mp4`/`.mov`/`.mkv` em `LOCAL_VIDEOS_DIR`.
2. Para cada vídeo não indexado (ou com `updated_at` anterior à data de modificação):
   - extrai duração via `ffprobe`;
   - extrai 3 frames (0%, 50%, 100%) via FFmpeg;
   - envia frames ao Gemini com prompt estruturado;
   - armazena `description`, `themes`, `orientation`, `has_face`, `duration`, caminhos dos frames.
3. Atualiza o SQLite.

### Comando `clone <url>`

1. **Download**: `downloader.py` baixa o Reels para `data/downloads/<id>.mp4`.
2. **Análise do Reels**:
   - extrai frames representativos;
   - obtém descrição textual com Gemini;
   - extrai texto na tela com Gemini;
   - obtém duração do vídeo e do áudio via `ffprobe`.
3. **Matching**:
   - carrega todos os vídeos indexados;
   - envia descrições locais + descrição do Reels ao Gemini e pede ranking top 3;
   - envia frames do Reels + frames dos 3 candidatos ao Gemini e pede escolha do melhor.
4. **Processamento**:
   - extrai áudio do Reels (`audio.aac`);
   - ajusta duração do vídeo local escolhido (`loop` ou `trim`);
   - detecta posição do rosto no vídeo local escolhido;
   - renderiza com FFmpeg `drawtext` posicionando o texto na região oposta ao rosto.
5. **Saída**: salva em `data/output/<timestamp>_<referencia_id>_final.mp4`.

---

## 6. Decisões Técnicas

### Modelo Gemini

- Usar `gemini-2.0-flash` como padrão. Modelo configurável via `GEMINI_MODEL`, mas o nome `gemini-3.5-flash` da especificação original não existe e foi ajustado para um modelo real e econômico.
- Chamadas multimodais enviam imagens PIL/frames diretamente via SDK `google-genai`.

### Extração de frames

- 3 frames por vídeo (início, meio, fim) para indexação e matching.
- Frame do meio para detecção de rosto.
- Para textos na tela, extrair frames a cada 1 segundo do Reels e concatenar resultados, removendo duplicatas.

### Ajuste temporal

- Se `D_video < D_audio`: replicar o vídeo local o suficiente (`ceil(D_audio / D_video)`) e cortar no final.
- Se `D_video > D_audio`: cortar no tempo exato do áudio.
- Implementado com `ffmpeg` (`-stream_loop` ou `concat`+`trim`).

### Posicionamento do texto

- Se rosto no topo/centro → texto na base.
- Se rosto na base → texto no topo.
- Padding de 80-120px das bordas.
- Estilo: fonte branca, contorno/sombra escura, tamanho proporcional à altura do vídeo.

### Banco de dados

- SQLite em `data/videos.db`.
- Tabela `videos` com colunas:
  - `id` (INTEGER PRIMARY KEY)
  - `path` (TEXT UNIQUE)
  - `filename` (TEXT)
  - `description` (TEXT)
  - `themes` (TEXT)
  - `orientation` (TEXT)
  - `duration_seconds` (REAL)
  - `has_face` (INTEGER)
  - `frame_paths` (TEXT, JSON)
  - `updated_at` (TIMESTAMP)

---

## 7. Interface da CLI

```bash
# Indexar vídeos locais
python -m src.main index

# Clonar Reels a partir de URL
python -m src.main clone <URL_DO_REELS>

# Opções úteis
python -m src.main clone <URL> --videos-dir "C:\...\Vídeos do fuga"
python -m src.main clone <URL> --output-dir "C:\...\output"
```

---

## 8. Tratamento de Erros

- Se `yt-dlp` falhar (URL inválida, privada, bloqueada): exibir erro e sair com código 1.
- Se `GEMINI_API_KEY` não estiver configurada: exibir mensagem clara de configuração.
- Se nenhum vídeo local estiver indexado: sugerir rodar `python -m src.main index` primeiro.
- Se o Gemini não encontrar texto na tela: prosseguir sem overlay de texto.
- Se a detecção de rosto falhar: posicionar texto na base como fallback.
- Todos os erros críticos são logados em `data/logs/`.

---

## 9. Validação (Definition of Done)

- [ ] Comando `index` processa todos os vídeos da pasta local sem erros.
- [ ] Banco SQLite contém descrições coerentes para cada vídeo local.
- [ ] Comando `clone <url>` baixa um Reels público do Instagram.
- [ ] Sistema seleciona um vídeo local plausível para o Reels fornecido.
- [ ] Vídeo final tem duração igual à do áudio do Reels.
- [ ] Áudio do Reels está sincronizado com o vídeo local.
- [ ] Texto extraído aparece sobreposto ao vídeo final.
- [ ] Texto não cobre a região do rosto (para vídeos com rosto detectável).

---

## 10. Cenários Futuros

- Integração com Wuzapi para receber URL do Reels e responder com vídeo final pelo WhatsApp.
- Webhook FastAPI para automação real-time.
- Filas (Celery/RQ) para processamento assíncrono.
- Cache de embeddings para matching mais rápido.
- Análise de timestamps do texto para legendas sincronizadas.
