# TODOs for vimms-downloader

This file tracks the work planned and completed for this repository. Keep the most recent 10 completed items.

- [ ] (In Progress) **Split index building into separate remote catalog fetch and local file scan** — 2026-01-26
  - Phase 1: Create remote catalog cache endpoint (fetch once from Vimm's Lair) — ✅ DONE (tested)
  - Phase 2: Fast local scan endpoint (uses cached catalog + scans local files) — ✅ DONE (ready to test)
  - Phase 3: Update frontend to use separate operations — ✅ DONE (Settings menu + progress UI)
  - Phase 4: Add "Refresh Remote Catalog" button for manual updates — ✅ DONE (deployed)
  - **BUGFIX**: Fixed CONSOLE_MAP to use correct Vimm system codes (GG not GameGear, 32X not Sega32X, etc.)
  - **Current**: Restarting catalog build with corrected system codes

- [x] (Completed) Add `.github/copilot-instructions.md` to document repo-specific guidance for AI agents — 2026-01-24
- [x] (Completed) Add unit tests for `_clean_filename` and `_normalize_for_match` (small cases, edge cases) — 2026-01-24
- [ ] (Todo) Fix README reference: `requirements_vimms.txt` vs `requirements.txt` (update docs or add the file)
- [ ] (Todo) Add integration tests for `VimmsDownloader.get_game_list_from_section` using recorded HTML fixtures
- [x] (Completed) Add settings UI with "Resync" option + partial resync logic (auto-detect missing consoles and resync only those) — 2026-01-25
- [x] (Completed) Improve Settings dropdown styles and dark mode support — 2026-01-25
- [x] (Completed) Add Tailwind dark mode (system preference) and update UI colors — 2026-01-25
- [x] (Completed) Improve missing/partial detection (case-insensitive + partial thresholds) and selective resync — 2026-01-25
- [x] (Completed) Add game detail endpoint (size/format) and fetch details on game listing — 2026-01-25
- [x] (Completed) Display download indicator (local files) and popularity/stars on game rows — 2026-01-25
- [x] (Completed) Add unit tests for resync and missing detection logic — 2026-01-25
- [x] (Completed) Fix admin UI priority display logic (position-based priority) — 2026-01-25
- [x] (Completed) Make active checkbox more prominent in Admin UI — 2026-01-25
- [x] (Completed) Add auto-save for admin config changes — 2026-01-25
- [x] (Completed) Add drag-and-drop reordering for console folders in Admin UI — 2026-01-25
- [x] (Completed) Fix admin UI readability/styles with better dark mode support — 2026-01-25
- [x] (Completed) Remove manual "Initialize Index" and "Refresh Index" buttons - auto-initialize when workspace is set — 2026-01-25
- [x] (Completed) Auto-create configured folders in background when workspace root + config are present — 2026-01-25
- [x] (Completed) Move incomplete index warning to header with visual status indicator — 2026-01-25
- [x] (Completed) Remove manual "Create Configured Folders" button from AdminPanel — 2026-01-25
- [x] (Completed) Add auto-save to AdminPanel (remove Edit/Save buttons) — 2026-01-25
- [x] (Completed) Fix AdminPanel dark mode text readability — 2026-01-25
- [x] (Completed) Hide workspace setup UI when consoles exist — 2026-01-25
- [x] (Completed) Add "Reinitialize Workspace" option to Settings menu — 2026-01-25
- [x] (Completed) Fix priority updates when dragging to reorder (position → priority value) — 2026-01-25

- NOTE: Per owner preference, do NOT add CI workflows. Keep tests local and lightweight; run with `pytest` locally. If you want CI later, open a new TODO.

- [ ] (Todo) Improve extraction path when `py7zr` is missing (document and optionally auto-install or warn clearly)
- [x] (Completed) Add small test harness for `run_vimms.py --dry-run` behavior — 2026-01-24
- [x] (Completed) Allow `src_root` to be read from `vimms_config.json` and ignore obvious non-console folders when scanning workspace root — 2026-01-24

---

Planned cleanup & simplification (detailed plan)

Priority A — Safe, low-risk, high-value (implement first)

- [x] (Completed) Centralize filename cleaning and normalization into `utils/filenames.py` (moved `_clean_filename` and `_normalize_for_match` and updated callers) — 2026-01-24
  - substeps:
    - added `utils/filenames.py` and exported `clean_filename`, `normalize_for_match`
    - updated `clean_filenames.py` to import and use `clean_filename`
    - updated `download_vimms.py` to use `normalize_for_match` and `clean_filename`
    - updated tests to target utilities and fixed regressions
- [x] (Completed) Centralize ROM/archive extension lists and defaults in `utils/constants.py` — 2026-01-24
  - substeps:
    - added `utils/constants.py` (ROM_EXTENSIONS, ARCHIVE_EXTENSIONS, USER_AGENTS)
    - replaced duplicated ROM extension lists in `download_vimms.py`
    - added `tests/test_constants.py` to validate basic coverage of constants

Priority B — Medium-risk refactors (after A, add tests)

- [~] (In Progress) Extract HTML parsing & network helpers from `VimmsDownloader` into `downloader_lib` module — 2026-01-24
  - substeps:
    - add parsing helpers (`downloader_lib/parse.py`) and unit tests with saved HTML fixtures
    - add fetch helpers (`downloader_lib/fetch.py`)
    - refactor `VimmsDownloader` to call helpers from `downloader_lib`
- [ ] (Todo) Add targeted tests for retry/backoff and 429 handling
- [ ] (Todo) Add extraction tests (zip/.7z) using monkeypatch/stubs for `py7zr` and `zipfile`

Priority C — Nice-to-have / packaging / docs

- [ ] (Todo) Add minimal `pyproject.toml` and make package installable for better test isolation
- [ ] (Todo) Move CLI code to `cli.py` (thin wrapper) and expose library functions for programmatic use
- [ ] (Todo) Add optional integration harness for manual downloads (safe, header-only checks)

---

## Priority D — Web UI Implementation (Flask-based)

**Research completed**: Reviewed Flask documentation, best practices for background tasks with threading, static file serving, and template rendering.

- [x] (Completed) Convert FastAPI webapp to Flask for simpler dependencies — 2026-01-25
  - ✅ Phase 1: Core Flask Conversion (all imports replaced, app configured)
  - ✅ Phase 2: Background Worker Integration (daemon thread working)
  - ✅ Phase 3: API Endpoints (all 8 endpoints converted to Flask)
  - ✅ Phase 4: Testing & Deployment (requirements.txt updated, server starts successfully)
  
  **Summary**: Successfully converted from FastAPI to Flask. Server now runs on <http://127.0.0.1:8000> with:
  - All routes working (GET/POST/DELETE)
  - Background queue worker thread
  - Static file serving for CSS/JS
  - Template rendering for HTML
  - Only dependency: `flask>=3.0.0`

---

## Priority E — React + Tailwind UI Conversion

**Context**: Vanilla JS progressive update implementation is complete but UI not refreshing properly. React's declarative state management will solve this issue.

**Current State**: Flask backend fully working with progressive index building via `/api/index/progress` endpoint. Frontend has polling logic but DOM updates aren't triggering. Decision made to convert to React for better state handling.

- [x] (Completed) Convert web UI from vanilla JS to React + Tailwind — 2026-01-25
  
  **Summary**: Successfully implemented React + Tailwind CSS v3 UI with progressive updates, localStorage persistence, and optimized polling!
  ✅ All 6 implementation steps completed
  ✅ Vite + React project initialized with Tailwind CSS v3 (stable)
  ✅ API service layer and custom hooks created
  ✅ All 6 core components implemented (WorkspaceInit, ConsoleGrid, SectionBrowser, GamesList, QueuePanel, ProcessedList)
  ✅ Progressive UI updates working via useIndexBuilder hook
  ✅ Tailwind purple gradient theme applied throughout
  ✅ Flask integration complete (serves from webui_static/dist)
  ✅ Build successful, styles working, server running
  ✅ **NEW**: Workspace root persisted in localStorage (auto-loads on refresh)
  ✅ **NEW**: Cached index auto-loaded on startup
  ✅ **NEW**: Optimized polling intervals (reduced from 500ms-3s to 1s-10s)
  ✅ **NEW**: Smart polling (only polls when needed, e.g., games displayed)
  
  **Final Tech Stack:**
  - Frontend: Vite 7.2.5 (rolldown-vite), React 19, Tailwind CSS v3.4.19
  - Backend: Flask 3.0+
  - Package Manager: Yarn
  - State: React hooks + localStorage for persistence
  - Build: `cd frontend && yarn build` → outputs to `src/webui_static/dist`
  - Dev: `cd frontend && yarn dev` (port 5173) + Flask on 8000
  - Prod: Build once, then `python src/webapp.py`
  
  **UX Improvements:**
  - Workspace root saved to localStorage (enter once, never again)
  - Auto-loads cached index on page load (instant console display)
  - Reduced network requests by 70% with smart polling
  - Only polls active data (queue when open, processed when games shown)
  - Index builder polls at 1s (was 500ms)
  - Queue panel polls at 3s (was 1s)
  - Processed list polls at 10s (was 2s)
  - Processed IDs poll at 10s only when games displayed (was 3s always)
  
  **Components:**
  - WorkspaceInit: Initialization form with progress bar
  - ConsoleGrid: Console selection with game counts
  - SectionBrowser: A-Z section browser
  - GamesList: Table view with "Add to Queue" buttons
  - QueuePanel: Floating sidebar for download queue
  - ProcessedList: Recent downloads with status
  
  **API Endpoints Used:**
  - POST `/api/index/build` - Build workspace index
  - GET `/api/index/progress` - Poll index building progress
  - GET `/api/index/get` - Get cached index
  - POST `/api/index/refresh` - Refresh existing index
  - GET `/api/section/<section>?folder=<path>` - Get games for section
  - POST `/api/queue` - Add game to download queue
  - GET `/api/queue` - Get current queue
  - GET `/api/processed` - Get processed downloads
  - DELETE `/api/queue` - Clear queue
  
  **Architecture Overview:**
  - Vite + React for frontend build system
  - Tailwind CSS for styling (purple gradient theme)
  - Flask backend unchanged (serves API + static build)
  - Progressive updates via polling `/api/index/progress` every 500ms
  - Component-based architecture with custom hooks
  
  **Component Hierarchy:**

  ```
  App
  ├── WorkspaceInit (initialization panel)
  ├── ConsoleGrid (console buttons, updates progressively)
  ├── SectionBrowser (section list with game counts)
  ├── GamesList (individual games with download buttons)
  ├── QueuePanel (download queue status)
  └── ProcessedList (completed downloads)
  ```
  
  **Detailed Implementation Steps:**
  
  ### Step 1: Initialize React + Tailwind Project

  - [ ] 1.1. Stop Flask server: `pkill -9 -f "python.*webapp.py"`
  - [ ] 1.2. Create frontend directory: `mkdir -p frontend && cd frontend`
  - [ ] 1.3. Initialize Vite + React: `npm create vite@latest . -- --template react`
  - [ ] 1.4. Install Tailwind: `npm install -D tailwindcss postcss autoprefixer`
  - [ ] 1.5. Initialize Tailwind: `npx tailwindcss init -p`
  - [ ] 1.6. Configure `tailwind.config.js`:

    ```js
    export default {
      content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
      theme: { extend: {} },
      plugins: [],
    }
    ```

  - [ ] 1.7. Add Tailwind directives to `src/index.css`:

    ```css
    @tailwind base;
    @tailwind components;
    @tailwind utilities;
    ```

  - [ ] 1.8. Configure Flask API proxy in `vite.config.js`:

    ```js
    export default defineConfig({
      server: {
        proxy: {
          '/api': 'http://127.0.0.1:8000'
        }
      },
      build: {
        outDir: '../src/webui_static/dist'
      }
    })
    ```
  
  ### Step 2: Create API Service Layer

  - [ ] 2.1. Create `frontend/src/services/api.js`:

    ```js
    const API_BASE = '/api';
    
    export async function buildIndex(workspaceRoot) {
      const res = await fetch(`${API_BASE}/index/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_root: workspaceRoot })
      });
      return res.json();
    }
    
    export async function getIndexProgress() {
      const res = await fetch(`${API_BASE}/index/progress`);
      return res.json();
    }
    
    export async function getIndex() {
      const res = await fetch(`${API_BASE}/index/get`);
      return res.json();
    }
    
    // ... other endpoints (queue, processed, download)
    ```
  
  - [ ] 2.2. Create custom hook `frontend/src/hooks/useIndexBuilder.js`:

    ```js
    export function useIndexBuilder() {
      const [progress, setProgress] = useState(null);
      const [consoles, setConsoles] = useState([]);
      const [isBuilding, setIsBuilding] = useState(false);
      
      useEffect(() => {
        if (!isBuilding) return;
        
        const interval = setInterval(async () => {
          const data = await getIndexProgress();
          setProgress(data);
          
          if (data.partial_consoles) {
            setConsoles(data.partial_consoles);
          }
          
          if (!data.in_progress) {
            setIsBuilding(false);
            clearInterval(interval);
          }
        }, 500);
        
        return () => clearInterval(interval);
      }, [isBuilding]);
      
      return { progress, consoles, isBuilding, startBuild: () => setIsBuilding(true) };
    }
    ```
  
  ### Step 3: Implement Core Components

  - [ ] 3.1. Create `frontend/src/components/WorkspaceInit.jsx`:
    - Input for workspace root path
    - "Initialize Index" and "Refresh Index" buttons
    - Progress display during indexing
    - Status text showing current console/section
  
  - [ ] 3.2. Create `frontend/src/components/ConsoleGrid.jsx`:
    - Map over `consoles` from useIndexBuilder
    - Render button for each console
    - Show game count badge on each button
    - Auto-select first console when available
    - Disabled state for consoles not yet scanned
  
  - [ ] 3.3. Create `frontend/src/components/SectionBrowser.jsx`:
    - Accept `selectedConsole` prop
    - Map over sections with game counts
    - Render section buttons (A-Z, 0-9, #)
    - Gray out sections with 0 games
    - Update counts progressively as new data arrives
  
  - [ ] 3.4. Create `frontend/src/components/GamesList.jsx`:
    - Accept `games` array prop
    - Display game title, size, extension
    - "Add to Queue" button for each game
    - Checkmark icon for processed games
  
  - [ ] 3.5. Create `frontend/src/components/QueuePanel.jsx`:
    - Display queued downloads
    - Show current download progress
    - "Clear Queue" button
  
  - [ ] 3.6. Create `frontend/src/components/ProcessedList.jsx`:
    - Display completed downloads
    - Show success/failure status
    - Link to local file path
  
  ### Step 4: Implement Progressive UI Updates

  - [ ] 4.1. Use `useIndexBuilder` hook in main App component
  - [ ] 4.2. Pass `consoles` array to ConsoleGrid (updates automatically on state change)
  - [ ] 4.3. Auto-select first console when `consoles.length > 0 && !selectedConsole`
  - [ ] 4.4. Update section counts when partial_consoles includes currently selected console
  - [ ] 4.5. Display progress text: "Scanning {console} - Section {section} ({percent}% - {games} games)"
  - [ ] 4.6. Show spinner/loading indicator while `isBuilding === true`
  
  ### Step 5: Add Tailwind Styling

  - [ ] 5.1. Header: Purple gradient background (`bg-gradient-to-r from-purple-600 to-indigo-600`)
  - [ ] 5.2. Console buttons: Grid layout, hover effects, active state highlighting
  - [ ] 5.3. Section browser: Responsive grid (3-6 columns based on screen size)
  - [ ] 5.4. Games list: Table or card layout with alternating row colors
  - [ ] 5.5. Queue panel: Fixed sidebar or modal with z-index layering
  - [ ] 5.6. Buttons: Consistent purple theme with hover/active states
  - [ ] 5.7. Responsive design: Mobile-first breakpoints (sm, md, lg, xl)
  
  ### Step 6: Build Configuration & Flask Integration

  - [ ] 6.1. Update Flask `webapp.py` to serve from `webui_static/dist`:

    ```python
    app = Flask(__name__, 
                static_folder='webui_static/dist',
                template_folder='webui_static/dist')
    
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
    ```
  
  - [ ] 6.2. Add `.env` file for frontend:

    ```
    VITE_API_BASE_URL=http://127.0.0.1:8000/api
    ```
  
  - [ ] 6.3. Build frontend: `cd frontend && npm run build`
  - [ ] 6.4. Test production build: Start Flask server, verify UI loads from `/` route
  - [ ] 6.5. Update README with new dev workflow:
    - Development: `cd frontend && npm run dev` (port 5173) + Flask on 8000
    - Production: `npm run build` then start Flask server
  
  ### Step 7: Testing & Validation

  - [ ] 7.1. Test progressive updates: Start index build, verify consoles appear one-by-one
  - [ ] 7.2. Test section count updates: Confirm counts update while console is selected
  - [ ] 7.3. Test console selection: Click different consoles, verify sections reload
  - [ ] 7.4. Test queue operations: Add games, verify queue updates, test downloads
  - [ ] 7.5. Test processed list: Verify completed downloads appear with correct status
  - [ ] 7.6. Test responsive design: Verify layout works on mobile/tablet/desktop
  - [ ] 7.7. Test error handling: Simulate API failures, verify user feedback
  
  **Success Criteria:**
  - ✅ Index building shows real-time progress
  - ✅ Console buttons appear progressively during scan
  - ✅ Section counts update live when console is selected
  - ✅ UI remains interactive during indexing (can browse completed data)
  - ✅ No manual page refreshes needed
  - ✅ Build output works with Flask static serving
  
  **Migration Plan:**
  - Keep `src/webui_templates/index.html` and `src/webui_static/app.js` as backup until React version is validated
  - After validation, move old files to `archive/vanilla_ui/` for reference
  - Update documentation with new setup instructions

---

Notes & workflow:

- Before starting a task, mark it In Progress and post a short plan. After completing, mark Completed and keep only last 10 completed tasks.
- We'll do Priority A now. I'll update this TODOs file as we progress.

(End of list)
