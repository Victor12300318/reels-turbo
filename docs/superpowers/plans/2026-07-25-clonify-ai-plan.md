# Clonify AI Rebranding, Schedule Management & Multi-AI Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebrand the application to **Clonify AI**, implement schedule editing/cancellation, and add Admin-controlled Multi-AI Provider support (Google Gemini & OpenRouter).

**Architecture:** Extend SQLite database with `system_settings` table, implement `PATCH` and `DELETE` endpoints for `/api/v1/jobs/{job_id}/schedule`, add `AIClientFactory` supporting OpenRouter REST API and Gemini SDK, and update frontend UI modals and admin settings.

**Tech Stack:** Python 3.11/3.13, FastAPI, SQLite, Next.js 14, Tailwind CSS, Lucide Icons, `google-genai`, `httpx`/`requests`.

## Global Constraints

- App name: **Clonify AI**
- Visual Style: ManyChat Light SaaS (`#F8FAFC`, `#FFFFFF`, `#0066FF`), zero emojis, Lucide SVG icons only.
- AI Provider Settings: Controlled exclusively by Admins in the Admin panel.

---

### Task 1: App Rebranding to Clonify AI

**Files:**
- Modify: `frontend/app/layout.tsx:1-25`
- Modify: `frontend/app/page.tsx:1-50`
- Modify: `frontend/app/login/page.tsx:1-100`

**Interfaces:**
- Consumes: Existing frontend layout and page metadata.
- Produces: Updated branding text ("Clonify AI") across all frontend pages.

- [ ] **Step 1: Update metadata in layout.tsx**

```tsx
export const metadata: Metadata = {
  title: 'Clonify AI - Automação e Clonagem Inteligente de Reels',
  description: 'Plataforma para automação e clonagem de Reels do Instagram',
}
```

- [ ] **Step 2: Update brand names in page.tsx and login/page.tsx**

In `page.tsx` header and login page, replace any remaining references to "Reels Cloner AI" with "Clonify AI".

- [ ] **Step 3: Verify frontend renders without errors**

Run tests with `pytest`.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/layout.tsx frontend/app/page.tsx frontend/app/login/page.tsx
git commit -m "style(branding): rebrand application title and headers to Clonify AI"
```

---

### Task 2: Database Schema & Admin System Settings Endpoint

**Files:**
- Modify: `src/database.py`
- Modify: `src/app.py`
- Test: `tests/test_database.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: SQLite `data/videos.db`
- Produces: `get_system_setting(key)`, `set_system_setting(key, value)`, `GET /api/v1/admin/settings`, `POST /api/v1/admin/settings`

- [ ] **Step 1: Write failing test in test_database.py**

```python
def test_system_settings_crud():
    from src.database import init_db, get_system_setting, set_system_setting
    init_db()
    set_system_setting("ai_provider", "openrouter")
    val = get_system_setting("ai_provider")
    assert val == "openrouter"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py -k test_system_settings_crud`

- [ ] **Step 3: Implement system_settings table and functions in src/database.py**

```python
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_system_setting(key: str, default: str = "") -> str:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_system_setting(key: str, value: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO system_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (key, value))
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Implement admin endpoints in src/app.py**

Add `GET /api/v1/admin/settings` and `POST /api/v1/admin/settings` (admin API Key protected).

- [ ] **Step 5: Run tests and verify pass**

Run: `pytest tests/test_database.py tests/test_app.py`

- [ ] **Step 6: Commit**

```bash
git add src/database.py src/app.py tests/test_database.py tests/test_app.py
git commit -m "feat(backend): implement system_settings table and admin API endpoints"
```

---

### Task 3: Backend Schedule Management (PATCH & DELETE Endpoints)

**Files:**
- Modify: `src/database.py`
- Modify: `src/app.py`
- Modify: `src/scheduler.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: Jobs table and background Scheduler.
- Produces: `PATCH /api/v1/jobs/{job_id}/schedule`, `DELETE /api/v1/jobs/{job_id}/schedule`

- [ ] **Step 1: Write failing tests in test_app.py**

```python
def test_update_and_cancel_schedule(client, auth_headers):
    # Create test job with status scheduled
    res = client.patch(
        "/api/v1/jobs/test-job-id/schedule",
        headers=auth_headers,
        json={"scheduled_at": "2026-08-01T15:00:00"}
    )
    assert res.status_code in (200, 404)
```

- [ ] **Step 2: Run test to verify behavior**

Run: `pytest tests/test_app.py -k test_update_and_cancel_schedule`

- [ ] **Step 3: Implement database and API handlers for scheduling**

In `src/database.py`:
```python
def update_job_schedule(job_id: str, scheduled_at: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs
        SET scheduled_at = ?, status = 'scheduled'
        WHERE id = ?
    """, (scheduled_at, job_id))
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected

def cancel_job_schedule(job_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs
        SET scheduled_at = NULL, status = 'completed'
        WHERE id = ?
    """, (job_id,))
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected
```

In `src/app.py`:
Add `@app.patch("/api/v1/jobs/{job_id}/schedule")` and `@app.delete("/api/v1/jobs/{job_id}/schedule")`.

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_app.py`

- [ ] **Step 5: Commit**

```bash
git add src/database.py src/app.py tests/test_app.py
git commit -m "feat(api): add PATCH and DELETE endpoints for job schedule management"
```

---

### Task 4: Unified AI Client Factory (Gemini & OpenRouter Support)

**Files:**
- Create: `src/ai_client.py`
- Modify: `src/matcher.py`
- Test: `tests/test_ai_client.py`

**Interfaces:**
- Consumes: `system_settings` table (for `ai_provider`, `openrouter_api_key`, `openrouter_model`)
- Produces: `get_ai_client()` returning unified multimodal vision interface.

- [ ] **Step 1: Write failing test for AI Client Factory**

```python
def test_ai_client_factory_selection():
    from src.ai_client import get_ai_client
    from src.database import set_system_setting
    set_system_setting("ai_provider", "gemini")
    client = get_ai_client()
    assert client.provider_name == "gemini"
```

- [ ] **Step 2: Implement src/ai_client.py**

Support Gemini via `google-genai` and OpenRouter via REST API calls.

- [ ] **Step 3: Run pytest**

Run: `pytest tests/test_ai_client.py`

- [ ] **Step 4: Commit**

```bash
git add src/ai_client.py tests/test_ai_client.py
git commit -m "feat(ai): create unified AI client supporting Gemini and OpenRouter"
```

---

### Task 5: Frontend Schedule Management (Edit Schedule Modal)

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `PATCH /api/v1/jobs/{job_id}/schedule` and `DELETE /api/v1/jobs/{job_id}/schedule`
- Produces: Interactive "Editar Agendamento" modal popup on scheduled job cards.

- [ ] **Step 1: Add modal state and handlers to page.tsx**

```tsx
const [editingJob, setEditingJob] = useState<Job | null>(null)
const [newScheduleTime, setNewScheduleTime] = useState('')
const [savingSchedule, setSavingSchedule] = useState(false)

const handleUpdateSchedule = async (jobId: string) => { ... }
const handleCancelSchedule = async (jobId: string) => { ... }
```

- [ ] **Step 2: Render Modal UI**

Include 9:16 preview, `datetime-local` input, "Salvar Novo Horário", and "Cancelar Agendamento" buttons.

- [ ] **Step 3: Verify build and test**

Run: `pytest`

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(ui): add schedule edit and cancellation modal to frontend"
```

---

### Task 6: Frontend Admin Panel for AI Providers

**Files:**
- Modify: `frontend/components/UserManagementTab.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/admin/settings` and `POST /api/v1/admin/settings`
- Produces: Admin settings panel for toggling Gemini vs OpenRouter and entering API keys.

- [ ] **Step 1: Add AI Settings section to UserManagementTab.tsx**

- [ ] **Step 2: Test API integration and state management**

- [ ] **Step 3: Commit**

```bash
git add frontend/components/UserManagementTab.tsx
git commit -m "feat(ui): add AI Provider configuration section in Admin panel"
```

---

### Task 7: Full System Verification & Git Push

- [ ] **Step 1: Run all tests with pytest**

Run: `pytest`
Expected: 100% pass (45+ tests).

- [ ] **Step 2: Push changes to main branch**

Run: `git push origin main`
