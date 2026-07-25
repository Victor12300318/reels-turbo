# GEMINI.md — Contexto de Instrução e Desenvolvimento

Este arquivo centraliza as diretrizes arquiteturais, padrões de código, comandos e fluxos de trabalho do projeto **Reels Cloner MVP**. É destinado a agentes de IA e desenvolvedores para garantir consistência e integridade em futuras modificações.

---

## 1. Visão Geral do Projeto

O **Reels Cloner MVP** é uma ferramenta CLI em Python 3.11+ para automatizar a clonagem de Reels do Instagram. A partir de uma URL de referência, o sistema baixa o Reels, analisa seus elementos visuais/auditivos e conteúdo de texto via Gemini, busca no acervo de vídeos locais o melhor correspondente e mescla ambos gerando um novo vídeo curto contendo o áudio original e um overlay de texto inteligente (que não cobre rostos).

### Tecnologias Principais
- **Linguagem:** Python 3.11+
- **Inteligência Artificial:** SDK `google-genai` (utilizando por padrão o modelo `gemini-2.0-flash` para tarefas multimodais de descrição, OCR e detecção de pontos de interesse/rostos)
- **Manipulação de Mídia:** FFmpeg e `ffprobe` (via chamadas de subprocesso do sistema)
- **Extração de Imagem:** `Pillow` (PIL) para tratamento de frames e passagem direta ao SDK Gemini
- **Download de Vídeos:** `yt-dlp` para baixar Reels públicos do Instagram
- **Banco de Dados:** SQLite (arquivo local `data/videos.db` para indexação persistente de metadados)
- **Testes:** `pytest` para testes unitários e de integração

---

## 2. Arquitetura e Estrutura do Código

O projeto segue um design modular e fortemente desacoplado:

```text
src/
├── __init__.py
├── main.py              # CLI e orquestração principal (comandos index e clone)
├── app.py               # Servidor FastAPI para a Webhook API local
├── config.py            # Centralização de configurações e variáveis de ambiente
├── database.py          # Acesso ao SQLite (repositório de vídeos indexados)
├── indexer.py           # Escaneamento de pastas e indexação de metadados locais
├── downloader.py        # Download de Reels via yt-dlp
├── analyzer.py          # Análise multimodal do Gemini (descrições, OCR, detecção facial)
├── matcher.py           # Ranqueamento híbrido e seleção de vídeos locais
├── video_processor.py   # Orquestração de tarefas FFmpeg (áudio, loop/trim, overlay)
├── ffmpeg_utils.py      # Funções de baixo nível de utilidade do FFmpeg/ffprobe
└── gemini_client.py     # Cliente unificado e autenticação com o SDK google-genai
```

### Fluxo de Dados e Ciclo de Vida

1. **Comando `index`:**
   - Lê todos os arquivos de vídeo em `LOCAL_VIDEOS_DIR` (definido nas configurações/.env).
   - Para vídeos novos/atualizados: extrai a duração com `ffprobe`, extrai 3 frames representativos com `ffmpeg_utils`, envia os frames ao Gemini via `VideoAnalyzer` para gerar descrições textuais ricas, temas e detecção facial básica.
   - Salva os metadados no SQLite em `data/videos.db`.

2. **Comando `clone <URL>`:**
   - Baixa o Reels de referência via `downloader.py` para `data/downloads/`.
   - Analisa o Reels baixado: extrai frames, faz OCR visual com Gemini e extrai texto estilizado e descrições.
   - Faz matching híbrido via `matcher.py`:
     1. Filtra os melhores candidatos locais comparando as descrições em formato de texto.
     2. Envia os frames do Reels e os frames do Top 3 candidatos ao Gemini para seleção multimodal final.
   - Executa processamento de mídia via `video_processor.py`:
     - Extrai áudio AAC do original.
     - Ajusta a duração do vídeo local escolhido (`loop` ou `trim`) para combinar com o áudio.
     - Detecta a posição aproximada do rosto no vídeo final (se houver).
     - Renderiza o vídeo usando FFmpeg `drawtext` para sobrepor o texto na posição oposta ao rosto (topo/base) com estilo legível (fonte branca e contorno escuro).

---

## 3. Ambiente e Execução

### Configuração do Ambiente

1. Crie e ative o ambiente virtual:
   ```bash
   python -m venv venv
   # No Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # No Linux/macOS:
   source venv/bin/activate
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure o arquivo `.env` a partir do modelo `.env.example`:
   ```env
   GEMINI_API_KEY=sua_chave_aqui
   GEMINI_MODEL=gemini-2.0-flash
   LOCAL_VIDEOS_DIR=C:\Users\victor.felix\Pictures\reels-turbo\Vídeos do fuga
   DATA_DIR=./data
   FRAMES_PER_VIDEO=3
   LOG_LEVEL=INFO
   ```

### Comandos CLI Principais

- **Indexação de Vídeos:**
  ```bash
  python -m src.main index
  ```

- **Clonagem de Reels:**
  ```bash
  python -m src.main clone "https://www.instagram.com/reel/ABC123/"
  ```

- **Clonagem especificando diretórios alternativos:**
  ```bash
  python -m src.main clone "https://www.instagram.com/reel/ABC123/" --output-dir "C:\Users\..."
  ```

### Webhook API local (FastAPI)

Para rodar a API localmente na porta 8000:
- **Via Python local:**
  ```bash
  uvicorn src.app:app --reload
  ```
- **Via Docker Compose (Recomendado, pois já inclui FFmpeg e fontes):**
  ```bash
  docker compose up reels-api
  ```

#### Endpoint `/api/clone` (POST)
Inicia o processo de clonagem do Reels de forma assíncrona. O vídeo final codificado em base64 será enviado diretamente para o webhook do n8n configurado.

- **Request JSON:**
  ```json
  {
    "url": "https://www.instagram.com/reel/DXu5TPCDtts/",
    "webhook_url": "https://n8n-n8n.example.com/webhook/abc-123"  // Opcional (se omitido, usa o padrão das configurações)
  }
  ```
- **Response JSON:**
  ```json
  {
    "status": "processing",
    "message": "A clonagem do Reels foi iniciada com sucesso em segundo plano! O vídeo final em base64 será enviado para o webhook do n8n.",
    "url": "https://www.instagram.com/reel/DXu5TPCDtts/",
    "webhook_target": "https://n8n-n8n.example.com/webhook/abc-123"
  }
  ```

- **Payload enviado para o Webhook do n8n (Success):**
  ```json
  {
    "status": "success",
    "url": "https://www.instagram.com/reel/DXu5TPCDtts/",
    "file_name": "filename.mp4",
    "video_base64": "JVBERi0xLjQK..." // Conteúdo do vídeo codificado em base64
  }
  ```

- **Payload enviado para o Webhook do n8n (Failure):**
  ```json
  {
    "status": "failed",
    "url": "https://www.instagram.com/reel/DXu5TPCDtts/",
    "error": "Descrição do erro ocorrido"
  }
  ```

### Execução via Docker
Para rodar sem dependências locais de FFmpeg:
```bash
docker compose build
docker compose run --rm reels-cloner python -m src.main index
docker compose up
```

---

## 4. Diretrizes e Convenções de Desenvolvimento

Para manter o codebase limpo e robusto, siga estritamente os seguintes padrões:

### Convenções de Código e Estilo
- **Tipagem Estrita:** Sempre declare tipos para parâmetros e retornos de funções. Use `typing.Any`, `dict`, `list`, `Union` (`|`), etc.
- **Tratamento de Caminhos:** Prefira `pathlib.Path` sobre strings brutas para manipulação e validação de caminhos de arquivos.
- **Formatação de Strings:** Use f-strings para formatação de logs e mensagens de erro.
- **Tratamento de Recursos:** Sempre libere conexões sqlite3 e feche arquivos PIL/imagens usando gerenciadores de contexto (`with`).
- **Logs:** Utilize o módulo `logging` configurado a partir de `src.main.setup_logging`. Evite `print` cru dentro de submódulos (mantenha `print` apenas na CLI de interface com o usuário).

### Convenções de Testes
- Todos os testes residem na pasta `tests/` seguindo a nomenclatura `test_<modulo>.py`.
- Utilize `pytest`.
- **Fixtures e Isolamento:** Use fixtures do `pytest` para simular dependências. Em testes de banco de dados, utilize a fixture `tmp_path` para criar bancos SQLite temporários em memória ou disco descartável.
- Para rodar a suíte completa de testes:
  ```bash
  pytest
  ```

### Uso da API Gemini
- Todas as chamadas para as APIs da Google Gemini devem passar por `GeminiClient` (`src/gemini_client.py`).
- Use imagens em formato PIL passadas diretamente ao SDK da biblioteca `google-genai`.
- Se as chamadas de OCR ou descrição falharem devido a problemas de rede ou chaves, trate graciosamente retornando strings vazias ou estruturas padrões de fallback para que a pipeline de processamento do vídeo não seja interrompida inteiramente.

### Padrão de Processamento de Vídeo (FFmpeg)
- Operações de subprocesso devem ser seguras. Sempre valide os códigos de retorno dos subprocessos do FFmpeg e capture `stderr` para depuração clara de eventuais falhas de codec ou comandos inválidos.
- Use `ffmpeg_utils.py` para as funções de utilidade reutilizáveis de mais baixo nível e guarde `video_processor.py` para a orquestração lógica de montagem final.

---

## 5. Diretrizes para Agentes de IA (Instruções Específicas)

Se você é um agente de IA operando nesta codebase:
1. **Não introduza bibliotecas extras** a menos que explicitamente solicitado ou verificado no `requirements.txt`.
2. **Preserve testes existentes:** Sempre execute `pytest` antes e depois de suas modificações para garantir conformidade e que não haja regressões.
3. **Novas Funcionalidades:** Se adicionar uma funcionalidade ou classe, crie o arquivo de teste correspondente na pasta `tests/`.
4. **Erros do FFmpeg:** Se uma chamada de FFmpeg falhar nos testes ou execução, extraia os logs completos do stderr para auxiliar o desenvolvedor no diagnóstico.
5. **Ajuste de Instruções:** Modifique este arquivo `GEMINI.md` apenas se houver mudanças estruturais aprovadas pelo time ou mudanças de arquitetura que influenciem as diretrizes de desenvolvimento do projeto.
