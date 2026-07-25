# Design Specification: Clonify AI Rebranding, Schedule Management & Multi-AI Providers

**Date:** 2026-07-25  
**Product Name:** Clonify AI  
**Status:** Approved  

## Overview
This specification outlines the technical design for rebranding the platform to **Clonify AI**, introducing comprehensive schedule management capabilities (editing post time and cancelling scheduled posts), and adding Admin-controlled Multi-AI Provider support (Google Gemini & OpenRouter).

---

## 1. Branding & Identity (Clonify AI)

- **Official Name:** Clonify AI
- **Frontend & App Metadata:**
  - Update `title` to "Clonify AI - Automação e Clonagem Inteligente de Reels"
  - Update application headers, branding elements, sidebars, page titles, browser notifications, and footers across `frontend/app/layout.tsx`, `frontend/app/page.tsx`, and `frontend/app/login/page.tsx`.
- **Visual Identity:**
  - Maintain the ManyChat Light SaaS aesthetic: clean `#F8FAFC` background, crisp white `#FFFFFF` cards, ManyChat Electric Blue `#0066FF` primary accents, Plus Jakarta Sans typography, subtle 3D depth hovers, zero emojis, and Lucide SVG icons.

---

## 2. Schedule Management (Editing & Cancellation)

### 2.1 Requirements
- Users must be able to change the scheduled date/time of any video job with status `'scheduled'`.
- Users must be able to cancel a scheduled post, which removes it from the automated publication queue and resets its status to `'completed'` (Ready for manual posting or re-scheduling).

### 2.2 Frontend UX (Edit Schedule Modal)
- In cards with status `'scheduled'` (in Cloner feed and Agenda tab), an **"Editar Agendamento"** button is displayed.
- Clicking the button opens a modal popup displaying:
  - 9:16 Video preview and post caption summary.
  - `datetime-local` input field initialized with the current `scheduled_at` timestamp.
  - **"Salvar Novo Horário"** primary button: sends `PATCH /api/v1/jobs/{job_id}/schedule` with `{ "scheduled_at": "YYYY-MM-DDTHH:MM:SS" }`.
  - **"Cancelar Agendamento"** danger/secondary button: sends `DELETE /api/v1/jobs/{job_id}/schedule`.

### 2.3 Backend API Endpoints (`src/app.py` & `src/database.py`)
- **`PATCH /api/v1/jobs/{job_id}/schedule`**:
  - Validates API key and user permissions.
  - Validates that `scheduled_at` is a valid ISO timestamp in the future.
  - Updates `scheduled_at` in the SQLite `jobs` table.
  - Re-queues/updates the job in the background `Scheduler` instance (`src/scheduler.py`).
  - Returns `{ "status": "success", "scheduled_at": "..." }`.
- **`DELETE /api/v1/jobs/{job_id}/schedule`**:
  - Validates API key and user permissions.
  - Clears `scheduled_at` to `NULL` and updates status from `'scheduled'` to `'completed'`.
  - Cancels any scheduled background task in `Scheduler`.
  - Returns `{ "status": "success", "message": "Agendamento cancelado com sucesso" }`.

---

## 3. Multi-AI Provider Architecture (Admin-Controlled OpenRouter & Gemini)

### 3.1 Requirements
- AI Provider selection is strictly controlled by Administrators in the Admin panel. Regular users cannot change or view AI keys.
- Supported Providers:
  - **Google Gemini** (Default: using `google-genai` SDK and `GEMINI_API_KEY`).
  - **OpenRouter** (REST API `https://openrouter.ai/api/v1/chat/completions` supporting models such as `google/gemini-2.0-flash-001`, `openai/gpt-4o-mini`, `anthropic/claude-3.5-haiku`, `deepseek/deepseek-r1`).

### 3.2 Database Schema (`system_settings` table)
New table `system_settings` in SQLite `data/videos.db`:
- `key` (TEXT PRIMARY KEY)
- `value` (TEXT)
- `updated_at` (DATETIME DEFAULT CURRENT_TIMESTAMP)

Default settings:
- `ai_provider`: `"gemini"`
- `openrouter_api_key`: `""`
- `openrouter_model`: `"google/gemini-2.0-flash-001"`

### 3.3 Factory Client (`src/ai_client.py` & `src/gemini_client.py`)
- Introduce `AIClient` abstract factory or unified client in `src/ai_client.py`.
- Queries `system_settings` table before executing multimodal video analysis / matching.
- If `ai_provider == "openrouter"` and `openrouter_api_key` is present:
  - Sends a POST request to OpenRouter Chat Completions endpoint with vision content formatted according to OpenRouter standards.
- Fallback: Defaults gracefully to Gemini API if OpenRouter key is missing or calls fail.

### 3.4 Admin Control Panel (`frontend/components/UserManagementTab.tsx`)
- Adds a **"Configurações do Sistema & IA (Admin)"** section visible only to admins:
  - Select AI Provider (`Google Gemini` vs `OpenRouter`).
  - OpenRouter API Key input.
  - OpenRouter Model text/dropdown input.
  - "Salvar Configurações de IA" button (`POST /api/v1/admin/settings`).

---

## 4. Testing & Verification

- **Backend Unit & Integration Tests (`pytest`):**
  - `tests/test_scheduler.py`: Test updating and cancelling job schedules.
  - `tests/test_app.py`: Test `PATCH /api/v1/jobs/{job_id}/schedule` and `DELETE /api/v1/jobs/{job_id}/schedule`.
  - `tests/test_ai_client.py`: Test `AIClient` switching between Gemini and OpenRouter providers.
- **Frontend Build Verification:**
  - Verify zero TypeScript or Next.js build errors.
  - Run full suite of automated tests (`pytest`) ensuring 100% pass rate.
