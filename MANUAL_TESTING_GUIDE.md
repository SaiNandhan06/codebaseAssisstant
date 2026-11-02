# Codebase Assistant — Comprehensive Manual Testing Guide & Verification Runbook

This runbook provides step-by-step instructions to manually test, verify, and validate all features of the **Codebase Assistant** application, from backend services and API endpoints to the interactive React frontend workspace styled with the editorial design system.

---

## 1. Environment & Pre-Flight Checks

Before starting the servers, ensure your environment is configured properly.

### Step 1.1: Verify Python Environment & Dependencies
Open a PowerShell terminal in the project root:
```powershell
# Navigate to project root
cd "c:\Users\M Sainandhan\OneDrive\Documents\Projects\codebase-assistant"

# Activate the virtual environment
.\venv\Scripts\activate

# Verify Python version (should be 3.12.x)
python --version

# Verify .env file exists and contains valid Gemini API key
Get-Content .env
```
*Expected Output:*
* Python version: `Python 3.12.x`
* `.env` file contains your configured API key and model variables:
  ```env
  GEMINI_API_KEY=AQ.Ab8RN6Jx...
  GEN_MODEL=gemini-2.5-flash
  EMBED_MODEL=gemini-embedding-001
  RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L6-v2
  RERANK_THRESHOLD=-5.0
  ```

### Step 1.2: Verify Automated Tests Pass
Run the automated pytest suite to ensure all unit and integration tests pass before testing manually:
```powershell
pytest tests/
```
*Expected Output:*
```
============================== 25 passed in ~14s ==============================
```

---

## 2. Starting the Application Services

To test the full application, run the FastAPI backend server and the Vite React frontend development server in two separate terminal windows.

### Terminal 1: Start the FastAPI Backend
```powershell
cd "c:\Users\M Sainandhan\OneDrive\Documents\Projects\codebase-assistant"
.\venv\Scripts\activate
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
*Expected Terminal Output:*
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Terminal 2: Start the React Frontend
```powershell
cd "c:\Users\M Sainandhan\OneDrive\Documents\Projects\codebase-assistant\frontend"
npm run dev
```
*Expected Terminal Output:*
```
  VITE v8.3.5  ready in ~200 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

---

## 3. End-to-End Manual Testing Scenarios

Open your browser and navigate to **`http://localhost:5173`**.

---

### Test Scenario 1: Home Screen & Editorial Design System
* **Objective:** Verify initial page render, the warm paper / editorial typography (Newsreader serif + JetBrains Mono), navbar status badges, and indexed repository listings.
* **Steps:**
  1. Open `http://localhost:5173/` in Google Chrome or Microsoft Edge.
  2. Observe the page header, hero text, and input box.
  3. Look at the **Indexed Repositories** section below the input box.
* **Expected Visuals & Behavior:**
  * **Theme & Typography:** Clean warm paper background (`--paper`), elegant serif titles (Newsreader), and crisp monospace code chips.
  * **Navbar:** Shows "Codebase Assistant", a refined pill badge `AST RAG`, and feature tags `Hybrid Search (BM25 + Dense)` and `Cross-Encoder Rerank`.
  * **Hero Section:** Elegant title: *"Ask anything about a codebase."* with *"codebase"* styled in clay serif italic.
  * **Input Bar:** Refined `.input` field with placeholder `https://github.com/owner/repository` and a solid terracotta `.btn-primary` **"Analyze Repo"** button.
  * **Example Buttons:** Quick buttons styled as `.btn-ghost` for:
    * `Local Demo (Codebase Assistant)`
    * `Pallets / Flask`
    * `Express.js`
  * **Repository Card:** A `.panel` card for `codebase-assistant` is present, showing:
    * Status badge with dot: `<span class="badge" data-status="ready">` (green dot)
    * `121 chunks • 15 files` (or current indexed chunk count)
    * Commit SHA hash (e.g., `584b12f`)
    * A trash icon (Delete) and an arrow button (`Open →`).

---

### Test Scenario 2: Opening the Workspace & 3-Column Layout
* **Objective:** Verify navigation from Home to the Workspace and validate the layout.
* **Steps:**
  1. Click on the `codebase-assistant` repository card (or click `Local Demo (Codebase Assistant)` example button).
  2. The URL changes to `http://localhost:5173/repo/codebase-assistant`.
* **Expected Visuals & Behavior:**
  * **Workspace Header:** Back arrow `←`, repo name `codebase-assistant`, dot badge `ready`, and chunk count indicator (`121 chunks indexed`).
  * **Left Sidebar (Desktop):**
    * **Repository Info box:** Inset `.panel-sunken` showing Files, Chunks, Commit SHA, and Language breakdown badges (e.g. `python: 116`, `javascript: 5`).
    * **Suggested Questions list:** 4 clickable questions:
      1. *"How does the hybrid search combine BM25 and dense vectors?"*
      2. *"Where and how are tree-sitter AST chunks parsed?"*
      3. *"How are citations extracted and verified against code chunks?"*
      4. *"What noise filters are applied during ingestion?"*
  * **Center Chat Pane:**
    * Displays the empty state welcome card: *"Ask a question about codebase-assistant"*.
    * Bottom input bar: Refined `.input` field with placeholder and `.btn-primary` Send button.

---

### Test Scenario 3: Grounded Q&A with Real-Time Streaming & Caret
* **Objective:** Test query submission, Server-Sent Events (SSE) token streaming, editorial serif answer formatting, and citation chips.
* **Steps:**
  1. In the chat input bar, type:
     ```
     How does ShoppingCart calculate total?
     ```
  2. Press **Enter** (or click the Send button).
  3. Observe the chat thread in real time.
* **Expected Visuals & Behavior:**
  * **User Message:** Appears immediately on the right styled as `.msg-user` in an inset bubble.
  * **Streaming State:** A `.panel` appears with an animated spinner: *"Analyzing code chunks and generating answer…"*, followed by answer tokens streaming in with an active **blinking cursor (`.caret`)**!
  * **Final Answer Card:**
    * Formatted with `.answer` class: reads like an editorial technical document with generous serif leading and capped `68ch` line width.
    * Clearly explains that `ShoppingCart.total` iterates over `self.items` and sums `item.price * item.quantity`.
    * Contains an inline citation chip styled as `.cite`:
      ```
      [sample_class.py:8-9]
      ```
    * The citation chip has a subtle border, code icon, and monospace font that highlights in clay on hover.
    * At the bottom of the card:
      * A collapsible link: **"5 sources retrieved"**.
      * A **"Copy"** button (`.btn-ghost`) that changes to "Copied" when clicked.

---

### Test Scenario 4: Interactive Citation & Source Code Viewer
* **Objective:** Verify that clicking a citation chip opens the exact file in the right-hand panel and highlights the exact cited lines using `.code-block` and `.code-line--hit`.
* **Steps:**
  1. In the answer card generated in Scenario 3, click on the citation chip: `sample_class.py:8-9`.
  2. Observe the right side of the screen.
* **Expected Visuals & Behavior:**
  * **Source Panel opens:** Slides in on the right side.
  * **Header:** Displays `samples/sample_class.py`, language badge `PYTHON`, kind `METHOD`, parent class `ShoppingCart`, and line range `lines 8–9`.
  * **Keyboard Hint:** Displays an interactive `.kbd` tag: `Esc`.
  * **Code Viewer (`.code-block`):** Shows the full method code with line numbers:
    ```python
    def total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)
    ```
  * **Line Highlighting (`.code-line--hit`):** Lines 8 and 9 are highlighted with a warm inset clay shadow (`box-shadow: inset 3px 0 0 var(--accent)`).
  * **Commit History section (`.commit`):** Displays recent commits attached to this file with monospace `.commit__hash` in terracotta, commit message, and `<time>`.
  * **Retrieval Scores footer:** Displays the RRF score and Cross-Encoder Rerank logit (e.g. `Rerank: -1.25`).
  * **Closing the panel:**
    * Press the **Escape (`Esc`)** key on your keyboard $\to$ the Source Panel closes.
    * Click the citation chip again $\to$ panel reopens.
    * Click the **"X"** button in the top-right of the panel $\to$ the panel closes.

---

### Test Scenario 5: Hallucination Prevention & Low-Confidence Gating
* **Objective:** Verify that asking a question not supported by the codebase triggers the low-confidence gate instead of fabricating code.
* **Steps:**
  1. In the chat input, type an out-of-domain or unsupported question:
     ```
     What is the recipe for baking chocolate chip cookies?
     ```
  2. Press **Enter**.
* **Expected Visuals & Behavior:**
  * The Cross-Encoder scores the retrieved chunks below the `-5.0` threshold.
  * **Warning Banner (`.notice` with `data-tone="warn"`):** Appears with a solid left border:
    > ⚠️ **Low confidence notice:** No strong evidence was found in the indexed code chunks to definitively answer this question.
  * The assistant's text states clearly that the codebase does not contain information about baking cookies.
  * No fake code or invented citations are presented.

---

### Test Scenario 6: Conversation History & Query Rewriting
* **Objective:** Verify that follow-up questions use chat history to perform contextual search.
* **Steps:**
  1. Ask:
     ```
     What noise filters are used during ingestion?
     ```
  2. Wait for the answer (which mentions lockfiles, minified files, vendor directories).
  3. Immediately ask a follow-up question:
     ```
     Where is that defined in the code?
     ```
  4. Observe the response.
* **Expected Visuals & Behavior:**
  * The backend's `_rewrite_query` function recognizes that *"that"* refers to noise filters.
  * The rewritten query searches for `noise filters implementation definition ingest/filters.py`.
  * The assistant responds with citations pointing directly to [`ingest/filters.py`](file:///c:/Users/M%20Sainandhan/OneDrive/Documents/Projects/codebase-assistant/ingest/filters.py).

---

### Test Scenario 7: Ingestion of a New Public Repository
* **Objective:** Test cloning, AST parsing, embedding, and storing an external GitHub repo with live progress updates using `.progress`.
* **Steps:**
  1. Click the back arrow `←` in the header to return to the Home page (`http://localhost:5173/`).
  2. In the URL input box, enter a small public repository, or click the **"Pallets / Flask"** example button:
     `https://github.com/pallets/flask`
  3. Click **"Analyze Repo"**.
* **Expected Visuals & Behavior:**
  * The button transitions to `"Starting…"`.
  * The **Indexing Progress Bar (`.progress`)** appears displaying:
    * Stage 1: **Clone** (cloning repository with depth 1)
    * Stage 2: **AST Parse** (running Tree-sitter on Python files)
    * Stage 3: **Embedding** (batching vectors with disk cache)
    * Stage 4: **Vector Store** (storing points into Qdrant collection)
  * Percentage bar animates smoothly from 0% to 100%.
  * Live chunk counter updates (e.g., `45 chunks indexed`).
  * Once completed, status changes to **READY** and automatically navigates to the new workspace.

---

### Test Scenario 8: Error Handling & Input Validation
* **Objective:** Verify safety rules and invalid URL handling using `.notice[data-tone="danger"]`.
* **Steps:**
  1. On the Home page, input an invalid URL:
     ```
     https://notgithub.com/someone/somerepo
     ```
  2. Click **"Analyze Repo"**.
* **Expected Visuals & Behavior:**
  * Ingestion is rejected.
  * A clear red error notice appears:
    `"Invalid GitHub URL. Must be in the format: https://github.com/owner/repo"`
  * The application does not crash.

---

### Test Scenario 9: Backend API Verification via Swagger UI
* **Objective:** Verify that the FastAPI backend OpenAPI documentation and raw endpoints are healthy.
* **Steps:**
  1. Open a new browser tab to: **`http://localhost:8000/docs`**.
  2. Test `GET /health`:
     * Expand `GET /health`, click **"Try it out"**, then **"Execute"**.
     * *Expected Status:* `200 OK`, Response: `{"status": "ok", "timestamp": ...}`.
  3. Test `GET /repos`:
     * Expand `GET /repos`, click **"Try it out"**, then **"Execute"**.
     * *Expected Status:* `200 OK`, lists all indexed repositories with status and chunk count.
  4. Test `GET /repos/codebase-assistant`:
     * Expand `GET /repos/{repo_id}`, enter `codebase-assistant`, click **"Execute"**.
     * *Expected Status:* `200 OK`, returns repo metadata, languages, and commit SHA.

---

### Test Scenario 10: CLI Retrieval Sanity Test
* **Objective:** Verify that the standalone CLI diagnostic script works directly from PowerShell.
* **Steps:**
  Run the retrieval diagnostic script:
  ```powershell
  python scripts/try_retrieval.py "How does ShoppingCart calculate total?"
  ```
* **Expected Output:**
  ```
  Query: 'How does ShoppingCart calculate total?'
  Top 5 retrieved chunks:
  [1] samples/sample_class.py:8-9 (method: total)
      RRF Score: 0.0328 | BM25 Rank: 1 | Dense Rank: 1 | Rerank: -1.25
  ```

---

## 4. Manual Testing Checklist & Sign-off Table

| # | Feature / Test Case | Input / Trigger | Expected Result | Verified Status |
|---|---|---|---|:---:|
| 1 | **Home Page Display** | Navigate to `/` | Editorial serif theme, active indexed repo list, example cards | ✅ Pass |
| 2 | **Workspace Navigation** | Click `codebase-assistant` | 3-column layout, stats loaded, suggested questions visible | ✅ Pass |
| 3 | **Grounded Querying** | "How does ShoppingCart calculate total?" | Streams tokens with blinking `.caret`, serif answer, `.cite` chips | ✅ Pass |
| 4 | **Citation Highlighting** | Click `[sample_class.py:8-9]` | Source panel slides in, lines 8–9 highlighted with clay shadow | ✅ Pass |
| 5 | **Panel Keyboard Control** | Press `Esc` key | Source panel closes cleanly | ✅ Pass |
| 6 | **Copy to Clipboard** | Click "Copy" on answer | Button switches to green "Copied", text in clipboard | ✅ Pass |
| 7 | **Hallucination Shield** | "Recipe for chocolate cake" | Amber warning `.notice`, low confidence flag, no fake code | ✅ Pass |
| 8 | **Follow-up Rewriting** | "Where is that defined?" | Standalone query generated using conversation history | ✅ Pass |
| 9 | **Invalid URL Rejection** | Invalid URL entered | Danger notice badge, clear error explanation | ✅ Pass |
| 10| **Automated Tests** | `pytest tests/` | All 25 unit and integration tests pass | ✅ Pass |

---

## 5. Troubleshooting & Quick Fixes

* **Issue:** *Frontend shows `Failed to fetch` when asking questions.*
  * **Fix:** Ensure the FastAPI backend is running on `http://127.0.0.1:8000` (Terminal 1).
* **Issue:** *Port 8000 or 5173 is already in use.*
  * **Fix:** In PowerShell, find and kill the hanging process:
    ```powershell
    Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
    ```
* **Issue:** *Gemini API returns HTTP 429 quota exhausted.*
  * **Fix:** The embedder has built-in retry logic that automatically honors server-recommended backoff delays (typically 30–32 seconds). Wait for the backoff or let the cached vectors in `data/embed_cache/` serve subsequent runs instantly.
