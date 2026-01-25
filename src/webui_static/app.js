// Cached index data loaded from server
let cachedIndex = null;
let currentConsole = null;
let currentSection = null;
let queuePollInterval = null;

// DOM elements
const folderPath = document.getElementById('folderPath');
const initBtn = document.getElementById('initFolder');
const refreshBtn = document.getElementById('refreshIndex');
const statusDiv = document.getElementById('status');
const consolesContainer = document.getElementById('consolesContainer');
const sectionsContainer = document.getElementById('sectionsContainer');
const gamesContainer = document.getElementById('gamesContainer');
const gamesLoading = document.getElementById('gamesLoading');
const sectionTitle = document.getElementById('sectionTitle');
const queueContainer = document.getElementById('queueContainer');
const processedContainer = document.getElementById('processedContainer');
const queueCount = document.getElementById('queueCount');
const clearQueueBtn = document.getElementById('clearQueue');

// Utility functions
function showStatus(message, type = 'info') {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
  setTimeout(() => {
    statusDiv.textContent = '';
    statusDiv.className = 'status';
  }, 5000);
}

async function fetchAPI(url, options = {}) {
  try {
    console.log('Fetching:', url, options);
    const response = await fetch(url, options);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    console.log('Response:', url, data);
    return data;
  } catch (error) {
    console.error('API Error:', error);
    showStatus(`API Error: ${error.message}`, 'error');
    throw error;
  }
}

// Initialize - build index for workspace root
async function buildIndex(workspaceRoot) {
  try {
    statusDiv.textContent = 'Starting workspace scan...';
    statusDiv.className = 'status info';
    initBtn.disabled = true;
    refreshBtn.disabled = true;

    // Clear existing UI
    consolesContainer.innerHTML = '<div class="loading">Scanning consoles...</div>';
    sectionsContainer.innerHTML = '';
    gamesContainer.innerHTML = '';

    let firstConsoleAutoSelected = false;

    // Start the build
    const buildPromise = fetchAPI('/api/index/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace_root: workspaceRoot })
    });

    // Poll for progress while building and update UI progressively
    const progressInterval = setInterval(async () => {
      try {
        const progress = await fetchAPI('/api/index/progress');
        if (progress.in_progress) {
          const percent = progress.consoles_total > 0
            ? Math.round((progress.consoles_done / progress.consoles_total) * 100)
            : 0;
          statusDiv.textContent = `Scanning ${progress.current_console} - Section ${progress.current_section} (${percent}% - ${progress.games_found} games found)`;

          // Update UI with partial consoles
          if (progress.partial_consoles && progress.partial_consoles.length > 0) {
            console.log(`[Progress] Updating UI with ${progress.partial_consoles.length} consoles`);
            displayPartialConsoles(progress.partial_consoles, workspaceRoot);

            // Auto-select first console once available
            if (!firstConsoleAutoSelected && progress.partial_consoles.length > 0) {
              firstConsoleAutoSelected = true;
              console.log(`[Progress] Auto-selecting first console: ${progress.partial_consoles[0].name}`);
              selectConsole(progress.partial_consoles[0]);
            }

            // Update current console's data if we're viewing it
            if (currentConsole) {
              const updatedConsole = progress.partial_consoles.find(c => c.name === currentConsole.name);
              if (updatedConsole) {
                console.log(`[Progress] Updating current console data: ${currentConsole.name}`);
                updateCurrentConsoleData(updatedConsole);
              }
            }
          } else {
            console.log('[Progress] No partial_consoles data yet');
          }
        } else {
          clearInterval(progressInterval);
        }
      } catch (e) {
        // Progress endpoint may fail, ignore
      }
    }, 500); // Poll every 500ms for smooth updates

    const data = await buildPromise;
    clearInterval(progressInterval);

    if (data.status === 'ok') {
      showStatus(`✓ Index built: ${data.consoles_count} consoles, ${data.total_games} games`, 'success');

      // Save workspace root to localStorage
      localStorage.setItem('vimms_workspace_root', workspaceRoot);

      // Load the fresh index
      await loadIndex();
    }
  } catch (error) {
    showStatus('Failed to build index', 'error');
  } finally {
    initBtn.disabled = false;
    refreshBtn.disabled = false;
  }
}

// Display partial consoles during progressive build
function displayPartialConsoles(consoles, workspaceRoot) {
  consolesContainer.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'loading';
  header.textContent = `Available Consoles (${consoles.length} scanned):`;
  consolesContainer.appendChild(header);

  const grid = document.createElement('div');
  grid.style.display = 'grid';
  grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(120px, 1fr))';
  grid.style.gap = '0.5rem';
  grid.style.marginTop = '0.5rem';

  consoles.forEach(console => {
    const btn = document.createElement('button');
    btn.className = 'section-btn';
    btn.textContent = `${console.name} (${console.system})`;
    btn.addEventListener('click', () => selectConsole(console));
    grid.appendChild(btn);
  });

  consolesContainer.appendChild(grid);
}

// Load cached index from server
async function loadIndex() {
  try {
    const data = await fetchAPI('/api/index/get');

    if (data.status === 'no_index') {
      showStatus('No index found. Enter workspace root and click Initialize.', 'info');
      consolesContainer.innerHTML = '';
      sectionsContainer.innerHTML = '';
      gamesContainer.innerHTML = '';
      return;
    }

    cachedIndex = data;
    console.log('Loaded index:', cachedIndex);

    // Update folder path from cached workspace root
    if (cachedIndex.workspace_root) {
      folderPath.value = cachedIndex.workspace_root;
      localStorage.setItem('vimms_workspace_root', cachedIndex.workspace_root);
    }

    // Display consoles
    displayConsoles();

    showStatus(`Loaded index: ${cachedIndex.consoles.length} consoles (${new Date(cachedIndex.timestamp).toLocaleString()})`, 'success');
  } catch (error) {
    if (error.message.includes('404')) {
      showStatus('No index found. Enter workspace root and click Initialize.', 'info');
    }
  }
}

// Display console list
function displayConsoles() {
  consolesContainer.innerHTML = '';
  sectionsContainer.innerHTML = '';
  gamesContainer.innerHTML = '';

  if (!cachedIndex || !cachedIndex.consoles || cachedIndex.consoles.length === 0) {
    consolesContainer.innerHTML = '<div class="loading">No consoles in index</div>';
    return;
  }

  const header = document.createElement('div');
  header.className = 'loading';
  header.textContent = `Available Consoles (${cachedIndex.consoles.length}):`;
  consolesContainer.appendChild(header);

  const grid = document.createElement('div');
  grid.style.display = 'grid';
  grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(120px, 1fr))';
  grid.style.gap = '0.5rem';
  grid.style.marginTop = '0.5rem';

  cachedIndex.consoles.forEach(console => {
    const btn = document.createElement('button');
    btn.className = 'section-btn';
    btn.textContent = `${console.name} (${console.system})`;
    btn.addEventListener('click', () => selectConsole(console));
    grid.appendChild(btn);
  });

  consolesContainer.appendChild(grid);
}

// Select a console and display its sections
function selectConsole(console) {
  currentConsole = console;
  currentSection = null;

  console.log('Selected console:', console);

  // Save selection
  localStorage.setItem('vimms_last_console', console.name);

  // Display sections
  sectionsContainer.innerHTML = '';
  gamesContainer.innerHTML = '';
  sectionTitle.textContent = `Console: ${console.name}`;

  SECTIONS.forEach(section => {
    const games = console.sections[section] || [];
    const btn = document.createElement('div');
    btn.className = 'section-btn';
    btn.textContent = `${section} (${games.length})`;

    // Only make clickable if section has data
    if (games.length > 0) {
      btn.addEventListener('click', () => selectSection(section));
    } else {
      btn.style.opacity = '0.5';
      btn.style.cursor = 'default';
    }

    sectionsContainer.appendChild(btn);
  });

  // Auto-select first non-empty section
  const firstSection = SECTIONS.find(s => (console.sections[s] || []).length > 0);
  if (firstSection) {
    selectSection(firstSection);
  } else {
    gamesContainer.innerHTML = '<div class="loading">Scanning sections...</div>';
  }
}

// Update the current console's sections as new data arrives
function updateCurrentConsoleData(partialConsole) {
  if (!currentConsole || currentConsole.name !== partialConsole.name) return;

  // Merge new section data
  currentConsole.sections = partialConsole.sections;

  // Re-render sections with updated counts
  SECTIONS.forEach((section, idx) => {
    const games = currentConsole.sections[section] || [];
    const btn = sectionsContainer.children[idx];
    if (btn) {
      btn.textContent = `${section} (${games.length})`;

      // Enable button if it now has games
      if (games.length > 0) {
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        // Re-add click handler
        btn.onclick = null;
        btn.addEventListener('click', () => selectSection(section));
      }
    }
  });

  // If currently viewing a section, update its games
  if (currentSection) {
    const games = currentConsole.sections[currentSection] || [];
    if (games.length > 0) {
      selectSection(currentSection);
    }
  } else {
    // Auto-select first available section
    const firstSection = SECTIONS.find(s => (currentConsole.sections[s] || []).length > 0);
    if (firstSection) {
      selectSection(firstSection);
    }
  }
}

// Select a section and display its games
function selectSection(section) {
  if (!currentConsole) return;

  currentSection = section;
  const games = currentConsole.sections[section] || [];

  sectionTitle.textContent = `${currentConsole.name} - Section: ${section} (${games.length} games)`;
  gamesContainer.innerHTML = '';

  // Update active button
  document.querySelectorAll('.section-btn').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.startsWith(section + ' '));
  });

  if (games.length === 0) {
    gamesContainer.innerHTML = '<div class="loading">No games in this section</div>';
    return;
  }

  games.forEach(game => {
    const gameDiv = document.createElement('div');
    gameDiv.className = 'game-item';

    const titleDiv = document.createElement('div');
    titleDiv.style.fontWeight = 'bold';
    titleDiv.textContent = game.name;

    const statusDiv = document.createElement('div');
    statusDiv.style.fontSize = '0.85em';
    statusDiv.style.color = game.present ? '#4CAF50' : '#999';
    statusDiv.textContent = game.present ? '✓ Already downloaded' : 'Not downloaded';

    const actionsDiv = document.createElement('div');
    actionsDiv.style.marginTop = '0.5rem';
    actionsDiv.style.display = 'flex';
    actionsDiv.style.gap = '0.5rem';

    if (game.present) {
      const removeBtn = document.createElement('button');
      removeBtn.textContent = '🗑 Remove';
      removeBtn.style.background = '#ff5722';
      removeBtn.style.color = 'white';
      removeBtn.style.border = 'none';
      removeBtn.style.padding = '0.25rem 0.75rem';
      removeBtn.style.borderRadius = '4px';
      removeBtn.style.cursor = 'pointer';
      removeBtn.addEventListener('click', () => {
        // TODO: Implement remove functionality
        showStatus('Remove functionality coming soon', 'info');
      });
      actionsDiv.appendChild(removeBtn);
    } else {
      const queueBtn = document.createElement('button');
      queueBtn.textContent = '📥 Queue Download';
      queueBtn.style.background = '#2196F3';
      queueBtn.style.color = 'white';
      queueBtn.style.border = 'none';
      queueBtn.style.padding = '0.25rem 0.75rem';
      queueBtn.style.borderRadius = '4px';
      queueBtn.style.cursor = 'pointer';
      queueBtn.addEventListener('click', () => queueGame(game));
      actionsDiv.appendChild(queueBtn);
    }

    gameDiv.appendChild(titleDiv);
    gameDiv.appendChild(statusDiv);
    gameDiv.appendChild(actionsDiv);
    gamesContainer.appendChild(gameDiv);
  });
}

// Queue a game for download
async function queueGame(game) {
  if (!currentConsole) return;

  try {
    await fetchAPI('/api/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        folder: currentConsole.folder,
        game: game,
        section: currentSection
      })
    });
    showStatus(`Queued: ${game.name}`, 'success');
    updateQueue();
    startQueuePolling();
  } catch (error) {
    showStatus('Failed to queue game', 'error');
  }
}

// Update queue display
async function updateQueue() {
  try {
    const data = await fetchAPI('/api/queue');
    queueCount.textContent = data.queue.length;

    queueContainer.innerHTML = '';
    if (data.queue.length === 0) {
      queueContainer.innerHTML = '<div class="loading">Queue is empty</div>';
      stopQueuePolling();
    } else {
      data.queue.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'queue-item';
        const gameName = item.game?.name || item.name || 'Unknown';
        itemDiv.textContent = gameName;
        queueContainer.appendChild(itemDiv);
      });
    }
    return data.queue;
  } catch (error) {
    console.error('Failed to update queue:', error);
    return [];
  }
}

// Update processed list
async function updateProcessed() {
  try {
    const data = await fetchAPI('/api/processed');

    processedContainer.innerHTML = '';
    if (data.processed.length === 0) {
      processedContainer.innerHTML = '<div class="loading">No processed items yet</div>';
    } else {
      data.processed.slice(0, 10).forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = `processed-item ${item.success ? 'success' : 'failed'}`;
        const gameName = item.item?.game?.name || item.item?.name || 'Unknown';
        const statusIcon = item.success ? '✓' : '✗';
        itemDiv.textContent = `${statusIcon} ${gameName}`;
        processedContainer.appendChild(itemDiv);
      });
    }
    return data.processed;
  } catch (error) {
    console.error('Failed to update processed:', error);
    return [];
  }
}

// Start polling queue only when there are active downloads
function startQueuePolling() {
  if (queuePollInterval) return; // Already polling

  queuePollInterval = setInterval(async () => {
    const queue = await updateQueue();
    await updateProcessed();

    // Stop polling when queue is empty
    if (queue.length === 0) {
      stopQueuePolling();
    }
  }, 3000);
}

function stopQueuePolling() {
  if (queuePollInterval) {
    clearInterval(queuePollInterval);
    queuePollInterval = null;
  }
}

// Clear queue
clearQueueBtn.addEventListener('click', async () => {
  if (!confirm('Are you sure you want to clear the download queue?')) {
    return;
  }

  try {
    await fetchAPI('/api/queue', { method: 'DELETE' });
    showStatus('Queue cleared', 'success');
    updateQueue();
  } catch (error) {
    showStatus('Failed to clear queue', 'error');
  }
});

// Initialize button handler
initBtn.addEventListener('click', async () => {
  const workspaceRoot = folderPath.value.trim();
  if (!workspaceRoot) {
    showStatus('Please enter workspace root folder path', 'error');
    return;
  }

  await buildIndex(workspaceRoot);
});

// Refresh button handler
refreshBtn.addEventListener('click', async () => {
  try {
    statusDiv.textContent = 'Starting refresh...';
    statusDiv.className = 'status info';
    refreshBtn.disabled = true;
    initBtn.disabled = true;

    // Start the refresh
    const refreshPromise = fetchAPI('/api/index/refresh', { method: 'POST' });

    // Poll for progress while refreshing
    const progressInterval = setInterval(async () => {
      try {
        const progress = await fetchAPI('/api/index/progress');
        if (progress.in_progress) {
          const percent = progress.consoles_total > 0
            ? Math.round((progress.consoles_done / progress.consoles_total) * 100)
            : 0;
          statusDiv.textContent = `Refreshing ${progress.current_console} - Section ${progress.current_section} (${percent}% - ${progress.games_found} games)`;
        } else {
          clearInterval(progressInterval);
        }
      } catch (e) {
        // Ignore
      }
    }, 500);

    const data = await refreshPromise;
    clearInterval(progressInterval);

    if (data.status === 'ok') {
      showStatus(`✓ Index refreshed: ${data.consoles_count} consoles, ${data.total_games} games`, 'success');
      await loadIndex();

      // Re-select current console if still available
      if (currentConsole) {
        const console = cachedIndex.consoles.find(c => c.name === currentConsole.name);
        if (console) {
          selectConsole(console);
        }
      }
    }
  } catch (error) {
    showStatus('Failed to refresh index', 'error');
  } finally {
    refreshBtn.disabled = false;
    initBtn.disabled = false;
  }
});

// Sections list (A-Z, number)
const SECTIONS = ['number', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
  'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'];

// Initial load
document.addEventListener('DOMContentLoaded', async () => {
  // Initial queue/processed update
  updateQueue();
  updateProcessed();

  // Try to load existing index
  await loadIndex();

  // If we have an index, auto-restore last console
  if (cachedIndex && cachedIndex.consoles.length > 0) {
    const lastConsoleName = localStorage.getItem('vimms_last_console');
    if (lastConsoleName) {
      const console = cachedIndex.consoles.find(c => c.name === lastConsoleName);
      if (console) {
        selectConsole(console);
      }
    }
  } else {
    // Auto-populate folder from localStorage
    const savedRoot = localStorage.getItem('vimms_workspace_root');
    if (savedRoot) {
      folderPath.value = savedRoot;
    }
  }
});
