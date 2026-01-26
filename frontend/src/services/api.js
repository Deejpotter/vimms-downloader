const API_BASE = '/api';

/**
 * Build the index for a workspace root
 */
export async function buildIndex(workspaceRoot) {
  const res = await fetch(`${API_BASE}/index/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_root: workspaceRoot })
  });
  if (!res.ok) throw new Error(`Failed to build index: ${res.statusText}`);
  return res.json();
}

/**
 * Get index building progress
 */
export async function getIndexProgress() {
  const res = await fetch(`${API_BASE}/index/progress`);
  if (!res.ok) throw new Error(`Failed to get progress: ${res.statusText}`);
  return res.json();
}

/**
 * Get the current index
 */
export async function getIndex() {
  const res = await fetch(`${API_BASE}/index/get`);
  if (!res.ok) throw new Error(`Failed to get index: ${res.statusText}`);
  return res.json();
}

/**
 * Refresh the index
 */
export async function refreshIndex() {
  const res = await fetch(`${API_BASE}/index/refresh`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to refresh index: ${res.statusText}`);
  return res.json();
}

/**
 * Build index fast using cached remote catalog
 */
export async function buildIndexFast(workspaceRoot) {
  const res = await fetch(`${API_BASE}/index/build_fast`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_root: workspaceRoot })
  });
  if (!res.ok) throw new Error(`Failed to build index fast: ${res.statusText}`);
  return res.json();
}

/**
 * Build remote catalog (one-time, takes 15-30 min)
 */
export async function buildRemoteCatalog(workspaceRoot) {
  const res = await fetch(`${API_BASE}/catalog/remote/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_root: workspaceRoot })
  });
  if (!res.ok) throw new Error(`Failed to build remote catalog: ${res.statusText}`);
  return res.json();
}

/**
 * Get remote catalog build progress
 */
export async function getRemoteCatalogProgress() {
  const res = await fetch(`${API_BASE}/catalog/remote/progress`);
  if (!res.ok) throw new Error(`Failed to get remote catalog progress: ${res.statusText}`);
  return res.json();
}

/**
 * Get cached remote catalog
 */
export async function getRemoteCatalog() {
  const res = await fetch(`${API_BASE}/catalog/remote/get`);
  if (!res.ok) throw new Error(`Failed to get remote catalog: ${res.statusText}`);
  return res.json();
}

/**
 * Get games for a section
 */
export async function getSectionGames(consoleKey, section) {
  const res = await fetch(`${API_BASE}/section/${section}?folder=${encodeURIComponent(consoleKey)}`);
  if (!res.ok) throw new Error(`Failed to get games: ${res.statusText}`);
  return res.json();
}

export async function resyncIndex(payload) {
  const res = await fetch(`${API_BASE}/index/resync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok && res.status !== 202) throw new Error(`Failed to resync: ${res.statusText}`);
  return res.json();
}

export async function getGameDetails(gameId, folder) {
  const res = await fetch(`${API_BASE}/game/${encodeURIComponent(gameId)}?folder=${encodeURIComponent(folder)}`);
  if (!res.ok) throw new Error(`Failed to get game details: ${res.statusText}`);
  return res.json();
}

/**
 * Add game to download queue
 */
export async function addToQueue(gameData) {
  const res = await fetch(`${API_BASE}/queue`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(gameData)
  });
  if (!res.ok) throw new Error(`Failed to add to queue: ${res.statusText}`);
  return res.json();
}

/**
 * Queue entire console for download (all sections)
 */
export async function queueConsole(folder, consoleName) {
  return addToQueue({
    type: 'console',
    folder,
    console_name: consoleName
  });
}

/**
 * Queue a single section for download
 */
export async function queueSection(folder, section, consoleName) {
  return addToQueue({
    type: 'section',
    folder,
    section,
    console_name: consoleName
  });
}

/**
 * Queue all active consoles for download (runs run_vimms.py)
 */
export async function queueAll(workspaceRoot) {
  return addToQueue({
    type: 'all',
    workspace_root: workspaceRoot
  });
}

/**
 * Get current download queue
 */
export async function getQueue() {
  const res = await fetch(`${API_BASE}/queue`);
  if (!res.ok) throw new Error(`Failed to get queue: ${res.statusText}`);
  return res.json();
}

/**
 * Get processed downloads list
 */
export async function getProcessed() {
  const res = await fetch(`${API_BASE}/processed`);
  if (!res.ok) throw new Error(`Failed to get processed: ${res.statusText}`);
  return res.json();
}

/**
 * Clear the download queue
 */
export async function clearQueue() {
  const res = await fetch(`${API_BASE}/queue`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to clear queue: ${res.statusText}`);
  return res.json();
}

/**
 * Initialize workspace (alternative to build)
 */
export async function initWorkspace(workspaceRoot) {
  const res = await fetch(`${API_BASE}/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_root: workspaceRoot })
  });
  if (!res.ok) throw new Error(`Failed to init workspace: ${res.statusText}`);
  return res.json();
}

/**
 * Get available sections list
 */
export async function getSections() {
  const res = await fetch(`${API_BASE}/sections`);
  if (!res.ok) throw new Error(`Failed to get sections: ${res.statusText}`);
  return res.json();
}
