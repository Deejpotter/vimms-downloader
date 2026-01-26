# Vimm's Downloader - Frequently Asked Questions & Troubleshooting

## Web UI Issues

### Q: The interface isn't updating when the index changes

**A:** The frontend polls for index updates automatically.

**How it works:**

1. `useIndexBuilder.js` polls every 500ms when index is building or incomplete
2. Auto-build starts when workspace is set
3. Yellow indicator in header shows build progress

**Code location:** `frontend/src/hooks/useIndexBuilder.js`

---

### Q: Only some console folders showing, but config has more systems

**A:** Index is still building or hasn't completed yet.

**Solution:**

1. Watch the yellow indicator in the header for build progress
2. Wait for index rebuild to complete
3. Configured console folders are auto-created during the build

**Backend auto-creates missing folders:** `src/webapp.py` lines 220-245 and 475-500

---

### Q: Changes to components not appearing in the browser

**A:** Frontend needs to be rebuilt after code changes.

**Solution:**

```bash
cd frontend
yarn build
```

Then **hard refresh** the browser (Ctrl+Shift+R or Cmd+Shift+R).

---

### Q: Index keeps restarting from scratch

**A:** This is now the expected behavior for incomplete consoles to ensure fresh data.

**How resume works:**

- Completed consoles (marked `complete: true`) are preserved
- Incomplete consoles are re-indexed to get latest data (ratings, file counts)
- Avoid file changes during builds to prevent Werkzeug auto-reload interruptions

**Code location:** `src/webapp.py` lines 225-262 and 966-1004

---

### Q: Folders aren't being saved in priority order in vimms_config.json

**A:** Backend sorts folders by priority when saving.

**Solution:**

- `api_config_save` sorts folders before writing: `src/webapp.py` lines 913-919
- Folders are automatically sorted by `priority` field (1-37)

---

## Game Data Issues

### Q: Game ratings not displaying

**A:** Ratings are extracted during index build from section pages.

**How it works:**

1. Rating is extracted from HTML during index build
2. Stored in `webui_index.json` per game
3. Frontend displays cached rating directly
4. Only completed consoles have full rating data

**Code location:** `downloader_lib/parse.py` (extraction), `src/webapp.py` (storage)

---

### Q: Downloaded column showing wrong status

**A:** Local presence is detected by comparing game titles to files on disk.

**How it works:**

- ✓ (green checkmark) if game is present on disk
- Download button if not present
- "Queued" button if download is in progress

**Code location:** `frontend/src/components/GamesList.jsx` lines 95-120

---

## Configuration & Setup

### Q: How do I add a new console system?

**A:** Add to vimms_config.json and the system will be auto-created:

```json
"folders": {
  "YourConsoleName": {
    "_comment": "Your console description",
    "active": true,
    "priority": 38
  }
}
```

**Note:** Use the Vimm's Lair system code as the folder name (see README_VIMMS.md for the full console table).

---

### Q: Folder priorities aren't being respected

**A:** Check the config file - folders are sorted by priority when saved.

**Files to check:**

- `vimms_config.json` (should be sorted by priority)
- `src/webapp.py` (save sorting in `api_config_save`)

---

## UI Components

### Q: Where did the Settings menu go?

**A:** The Settings menu, ResyncModal, and AdminPanel were removed to simplify the UI.

**Current interface:**

- Auto-build indicator (yellow) shows index status
- No manual sync or index controls needed
- Index builds automatically when workspace is set
- Resume logic handles incomplete consoles automatically

**Files removed from render:**

- `SettingsMenu.jsx` (dropdown in header)
- `ResyncModal.jsx` (manual resync dialog)
- `AdminPanel.jsx` (console configuration UI)

**Code location:** `frontend/src/App.jsx` (simplified main component)

---

## Dark Mode Issues

### Q: Some panels are still light in dark mode

**A:** Add Tailwind dark mode classes to components.

**Solution:** Add dark mode variants:

- `dark:bg-gray-800` (backgrounds)
- `dark:text-white` or `dark:text-gray-300` (text)
- `dark:border-gray-700` (borders)
- `dark:bg-gray-700` (secondary backgrounds)

**Files to check:**

- `GamesList.jsx`
- `ProcessedList.jsx`
- `SectionBrowser.jsx`
- `ConsoleGrid.jsx`
- `QueuePanel.jsx`

---

## Server & Deployment

### Q: Flask server isn't starting or crashes immediately

**A:** Check these common issues:

1. **Port already in use:**

   ```bash
   # Kill existing process on port 8000
   netstat -ano | findstr :8000
   taskkill /PID <process_id> /F
   ```

2. **Missing dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Python version:**
   - Requires Python 3.8+
   - Check with `python --version`

---

### Q: Changes to Python code not taking effect

**A:** Flask auto-reloader should catch changes, but sometimes needs manual restart.

**Solution:**

1. Stop server (Ctrl+C)
2. Restart: `cd src && python webapp.py`
3. Check logs for errors during startup

---

## Development Workflow

### Q: What's the proper workflow for making UI changes?

**A:** Follow this sequence:

1. **Edit React components** in `frontend/src/components/`
2. **Rebuild frontend:**

   ```bash
   cd frontend
   yarn build
   ```

3. **Flask auto-reloads** (if running in debug mode)
4. **Hard refresh browser** (Ctrl+Shift+R)

For development with hot reload:

```bash
# Terminal 1: Flask backend
cd src && python webapp.py

# Terminal 2: Vite dev server
cd frontend && yarn dev
# Visit http://localhost:5173
```

---

### Q: How do I debug index building issues?

**A:** Multiple log levels available:

1. **Flask logs:** Terminal where `webapp.py` runs
   - Shows API calls, index progress, errors

2. **Browser console:** Network tab + Console
   - Check `/api/index/progress` calls
   - Verify console data structure

3. **Check index file:**

   ```bash
   cat src/webui_index.json | jq '.consoles[] | .name'
   ```

4. **Enable verbose logging:**

   ```python
   logger.setLevel(logging.DEBUG)
   ```

---

## Known Issues & Limitations

### Missing game details at index time

**Current behavior:** Size/format/rating fetched on-demand when user clicks a section.

**Why:** Fetching individual game pages during index build would take hours for thousands of games.

**Workaround:** Frontend fetches details for first 10 visible games automatically.

---

### Drag-and-drop doesn't work on touch devices

**Current behavior:** Only mouse drag events supported.

**Workaround:** Use up/down arrow buttons (not yet implemented).

**TODO:** Add touch event handlers or use a library like `react-beautiful-dnd`.

---

### Some console folders show warning icons after creation

**Expected behavior:** Folders just created during index build show as "exists: false" until next scan.

**Solution:** Click section letter to refresh, or rebuild index again.

---

## Getting Help

### Q: Where should I report bugs or request features?

**A:**

1. Check this FAQ first
2. Review `README.md` and `.github/copilot-instructions.md`
3. Check `.github/TODOs.md` for known issues
4. Create an issue with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Browser console errors
   - Flask server logs

---

### Q: How do I enable debug logging?

**A:**

**Backend (Flask):**
Already enabled in debug mode. Check terminal output.

**Frontend (Browser):**
Open DevTools (F12) → Console tab. Check for:

- Network errors (red)
- Failed API calls
- React warnings

**Index building:**
Watch yellow progress banner and check `/api/index/progress` in Network tab.

---

## Performance Tips

### Slow index building

- **Expected:** ~1-3 seconds per section (A-Z + numbers = 27 sections per console)
- **For 33 consoles:** ~15-30 minutes total
- **Runs in background:** You can browse already-scanned consoles while others load

### Reduce initial scan time

1. Edit `vimms_config.json`
2. Set consoles to `"active": false` if you don't need them
3. Reinitialize workspace

### Frontend performance

- First 10 games in each section fetch details automatically
- Scroll down to load more (not yet implemented - currently loads all)
- Consider pagination for sections with 100+ games

---

## File Locations Reference

| Component | File Path |
|-----------|-----------|
| Main Flask app | `src/webapp.py` |
| Downloader core | `src/download_vimms.py` |
| HTML parsing | `downloader_lib/parse.py` |
| React main app | `frontend/src/App.jsx` |
| Console grid | `frontend/src/components/ConsoleGrid.jsx` |
| Games list | `frontend/src/components/GamesList.jsx` |
| Admin panel | `frontend/src/components/AdminPanel.jsx` |
| Index builder hook | `frontend/src/hooks/useIndexBuilder.js` |
| API client | `frontend/src/services/api.js` |
| Config file | `vimms_config.json` |
| Cached index | `src/webui_index.json` |
| Download queue | `src/webui_queue.json` |
| Build output | `src/webui_static/dist/` |

---

## Quick Command Reference

```bash
# Start Flask server
cd src && python webapp.py

# Build frontend
cd frontend && yarn build

# Dev mode with hot reload
cd frontend && yarn dev

# Install dependencies
pip install -r requirements.txt
cd frontend && yarn install

# Run tests
pytest tests/

# Clean rebuild
rm src/webui_index.json
# Then reinitialize in Settings
```

---
