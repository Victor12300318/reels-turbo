# Reels Cloner MVP

Automatiza a clonagem de Reels: baixa um vídeo de referência do Instagram, escolhe o melhor vídeo local da sua pasta e gera um novo vídeo com o áudio e texto do original.

## Requisitos

- Python 3.11+
- FFmpeg instalado e disponível no PATH (ou Docker)
- Conta e chave de API do Google Gemini

## Instalação

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha:

```bash
GEMINI_API_KEY=sua_chave_aqui
```

## Uso

1. Indexe seus vídeos locais (análise feita apenas uma vez, reindexa quando novos vídeos são adicionados):

```bash
python -m src.main index
```

2. Clone um Reels a partir da URL:

```bash
python -m src.main clone "https://www.instagram.com/reel/ABC123/"
```

O vídeo final será salvo em `data/output/`.

### Opcional: passar pasta de vídeos e saída

```bash
python -m src.main index
python -m src.main clone "https://www.instagram.com/reel/ABC123/" --output-dir "C:\..."
```

## Docker

```bash
docker compose build
docker compose run --rm reels-cloner python -m src.main index
docker compose up
```

## Estrutura

- `src/main.py` — CLI
- `src/config.py` — variáveis de ambiente
- `src/indexer.py` — indexação dos vídeos locais
- `src/downloader.py` — download do Reels com `yt-dlp`
- `src/analyzer.py` — descrição, OCR e detecção de rosto via Gemini
- `src/matcher.py` — seleção do melhor vídeo local (híbrido)
- `src/video_processor.py` — manipulação de áudio/vídeo com FFmpeg
- `src/database.py` — metadados no SQLite

## Limitações do MVP

- O texto do Reels é aplicado como overlay estático no vídeo final.
- A integração com WhatsApp/Wuzapi é um próximo passo.
- Escolha final do vídeo local é automática, sem revisão do usuário.
