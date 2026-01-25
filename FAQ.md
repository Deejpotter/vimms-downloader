# Vimm's Downloader - Frequently Asked Questions & Troubleshooting

## Web UI Issues

### Q: The interface isn't updating when the index changes
**A:** The frontend needs to poll more frequently and watch for incomplete index status.

**Solution:**
1. Check that `useIndexBuilder.js` polls when `isBuilding` OR `isIncomplete` is true
2. Reduce polling interval to 500ms for responsive updates
3. Make sure the dependency array includes both `[isBuilding, isIncomplete]`

**Code location:** `frontend/src/hooks/useIndexBuilder.js`

---

### Q: Only 12 console folders showing, but config has 33 systems
**A:** The cached index was built before auto-creation logic was added.

**Solution:**
1. Click **Settings** (top right)
2. Click **Reinitialize Workspace**
3. Wait for index rebuild to complete (shows progress in yellow banner)
4. All 33 configured console systems will be created automatically

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

### Q: "Index incomplete - auto-building..." message but nothing happens in logs
**A:** The backend wasn't detecting incomplete index and starting auto-rebuild.

**Solution:**
- Fixed in `src/webapp.py` `init_worker()` function (lines 1257-1275)
- Now checks `CACHED_INDEX.get('complete') == False` and starts background rebuild
- Restart Flask server to apply changes

---

### Q: Folders aren't being saved in priority order in vimms_config.json
**A:** Backend needs to sort folders by priority when saving.

**Solution:**
- `api_config_save` now sorts folders before writing: `src/webapp.py` lines 913-919
- Folders are automatically sorted by `priority` field (1-37)

---

## Game Data Issues

### Q: Game size, format, and rating not displaying
**A:** Multiple issues:
1. Game ID field mismatch (`game_id` vs `id`)
2. Missing import for `parse_game_details`
3. Frontend calls backend, but backend wasn't mapping fields correctly

**Solutions:**
1. Fixed game ID mapping in `src/webapp.py`:
   - Changed `game.get('id', '')` → `game.get('game_id', '')`
   - Changed `game.get('url', '')` → `game.get('page_url', '')`
2. Added import: `from downloader_lib.parse import parse_game_details`
3. Backend endpoint already exists: `/api/game/<game_id>` fetches details on-demand

**Files modified:**
- `src/webapp.py` (lines 272, 532)
- `downloader_lib/parse.py` (added `parse_game_details` function)
- `src/download_vimms.py` (line 50)

---

### Q: Downloaded column showing wrong status
**A:** Frontend needs to distinguish between "present on disk" vs "recently downloaded".

**Solution:**
- Updated `GamesList.jsx` to show:
  - ✓ (green checkmark) if `isPresent === true`
  - ✗ (red X) + Download button if not present
  - "Queued" button if `isProcessed === true`

**Code location:** `frontend/src/components/GamesList.jsx` lines 95-120

---

## Configuration & Setup

### Q: How do I add a new console system?
**A:** Two steps required:

1. **Add to CONSOLE_MAP** in `src/download_vimms.py` and `download_vimms.py`:
   ```python
   CONSOLE_MAP = {
       'YourConsole': 'YourConsoleName',
       # ... existing entries
   }
   ```

2. **Add to vimms_config.json**:
   ```json
   "folders": {
     "YourConsole": {
       "_comment": "Your console description",
       "active": true,
       "priority": 38
     }
   }
   ```

3. **Reinitialize workspace** in Settings to create folders and scan games

---

### Q: Folder priorities aren't being respected
**A:** Check these areas:

1. **Display order** - AdminPanel should sort by priority:
   ```javascript
   .sort((a, b) => (a[1].priority || 0) - (b[1].priority || 0))
   ```

2. **Save order** - Backend sorts before saving (see above)

3. **Load order** - Config file is now pre-sorted by priority

**Files to check:**
- `frontend/src/components/AdminPanel.jsx` (display sorting)
- `src/webapp.py` (save sorting in `api_config_save`)

---

## Dark Mode Issues

### Q: Some panels are still light in dark mode
**A:** Missing Tailwind dark mode classes.

**Solution:** Add dark mode variants to all components:
- `dark:bg-gray-800` (backgrounds)
- `dark:text-white` or `dark:text-gray-300` (text)
- `dark:border-gray-700` (borders)
- `dark:bg-gray-700` (secondary backgrounds)

**Files affected:**
- `AdminPanel.jsx`
- `GamesList.jsx`
- `ProcessedList.jsx`
- `SectionBrowser.jsx`
- `ConsoleGrid.jsx`
- `QueuePanel.jsx`

---

## Auto-Save Issues

### Q: Auto-save firing too many times during drag-and-drop
**A:** Two problems:
1. Debounce too short (1.5s)
2. No check to skip save during active drag

**Solution:**
1. Increased debounce to 3 seconds
2. Added condition: `if (draggedIndex !== null) return;`

**Code location:** `frontend/src/components/AdminPanel.jsx` lines 85-95

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
