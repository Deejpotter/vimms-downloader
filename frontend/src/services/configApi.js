const API_BASE = '/api';

export async function getConfig() {
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error('Failed to fetch config');
  return res.json();
}

export async function saveConfig(cfg) {
  const res = await fetch(`${API_BASE}/config/save`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg)
  });
  if (!res.ok) throw new Error('Failed to save config');
  return res.json();
}

export async function createConfiguredFolders(payload) {
  const res = await fetch(`${API_BASE}/config/create_folders`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to create folders');
  return res.json();
}

export async function getDefaultFolders() {
  const res = await fetch(`${API_BASE}/config/default_folders`);
  if (!res.ok) throw new Error('Failed to fetch default folders');
  const data = await res.json();
  return data.defaults || {};
}