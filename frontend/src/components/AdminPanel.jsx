import { useEffect, useState } from 'react';
import { getConfig, saveConfig, createConfiguredFolders } from '../services/configApi';

export default function AdminPanel({ open, onClose }) {
  const [config, setConfig] = useState(null);
  const [editing, setEditing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createdFolders, setCreatedFolders] = useState([]);
  const [draggedIndex, setDraggedIndex] = useState(null);

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const cfg = await getConfig();
        setConfig(cfg);
      } catch (e) {
        console.error('Failed to load config:', e);
      }
    })();
  }, [open]);

  // Auto-save config changes after delay, but skip during active drag or when config is invalid
  useEffect(() => {
    if (!config || !open || draggedIndex !== null) return;

    // Do not autosave if folders are empty or workspace_root is missing
    const foldersEmpty = !config.folders || Object.keys(config.folders).length === 0;
    const noWorkspace = !config.workspace_root || String(config.workspace_root).trim() === '';
    if (foldersEmpty || noWorkspace) return;

    const timer = setTimeout(async () => {
      try {
        await saveConfig(config);
      } catch (e) {
        console.error('Auto-save failed:', e);
      }
    }, 3000);
    return () => clearTimeout(timer);
  }, [config, open, draggedIndex]);

  const handleToggleActive = (key) => {
    setConfig(prev => ({
      ...prev,
      folders: {
        ...prev.folders,
        [key]: { ...prev.folders[key], active: !prev.folders[key].active }
      }
    }));
  };

  const handlePriorityChange = (key, val) => {
    setConfig(prev => ({
      ...prev,
      folders: {
        ...prev.folders,
        [key]: { ...prev.folders[key], priority: Number(val) }
      }
    }));
  };

  // Simple reorder: move item up/down
  const moveFolder = (key, direction) => {
    const entries = Object.entries(config.folders).sort((a, b) => (a[1].priority || 0) - (b[1].priority || 0));
    const idx = entries.findIndex(([k]) => k === key);
    if (idx < 0) return;
    const newIdx = direction === 'up' ? Math.max(0, idx - 1) : Math.min(entries.length - 1, idx + 1);
    const item = entries.splice(idx, 1)[0];
    entries.splice(newIdx, 0, item);
    updatePriorities(entries);
    const newFolders = Object.fromEntries(entries);
    setConfig(prev => ({ ...prev, folders: newFolders }));
  };

  // Update priorities based on position (1, 2, 3...)
  const updatePriorities = (entries) => {
    entries.forEach(([key, val], idx) => {
      val.priority = idx + 1;
    });
  };

  // Drag-and-drop handlers
  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (draggedIndex === null || draggedIndex === index) return;
    
    const entries = Object.entries(config.folders).sort((a, b) => (a[1].priority || 0) - (b[1].priority || 0));
    const draggedItem = entries[draggedIndex];
    entries.splice(draggedIndex, 1);
    entries.splice(index, 0, draggedItem);
    updatePriorities(entries);
    const newFolders = Object.fromEntries(entries);
    setConfig(prev => ({ ...prev, folders: newFolders }));
    setDraggedIndex(index);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDraggedIndex(null);
  };

  const handleSave = async () => {
    try {
      await saveConfig(config);
      setEditing(false);
      alert('Config saved');
    } catch (e) {
      alert('Failed to save config: ' + e.message);
    }
  };

  const handleCreateFolders = async () => {
    if (!config || !config.defaults) return;
    const root = config.defaults.src_root || config.workspace_root || '';
    if (!root) {
      alert('Workspace root not set in config; please enter it first.');
      return;
    }
    setCreating(true);
    setCreatedFolders([]);
    try {
      const res = await createConfiguredFolders({ workspace_root: root, active_only: true });
      setCreatedFolders(res.created || []);
    } catch (e) {
      alert('Failed to create folders: ' + e.message);
    } finally {
      setCreating(false);
    }
  };

  if (!open) return null;
  if (!config) return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white dark:bg-gray-900 dark:text-white rounded-lg p-6 w-96 shadow-lg">Loading config...</div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-3/4 max-w-4xl max-h-[90vh] shadow-lg flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold dark:text-white">Admin — vimms_config.json</h2>
          <button onClick={() => onClose()} className="px-3 py-1 rounded bg-gray-100 dark:bg-gray-700 dark:text-white">Close</button>
        </div>

        <div className="grid grid-cols-2 gap-6 overflow-y-auto">
          <div>
            <h3 className="font-medium dark:text-white">Folders</h3>
            <div className="mt-2 border rounded bg-gray-50 p-3 dark:bg-gray-800 dark:border-gray-700">
              {Object.entries(config.folders || {})
                .sort((a, b) => (a[1].priority || 0) - (b[1].priority || 0))
                .map(([key, v], index) => (
                <div
                  key={key}
                  draggable
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDrop={handleDrop}
                  className={`flex items-center justify-between gap-2 py-2 border-b last:border-b-0 dark:border-gray-700 cursor-move ${draggedIndex === index ? 'opacity-50' : ''}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col gap-0.5">
                      <button onClick={() => moveFolder(key, 'up')} className="px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-600 dark:text-white rounded">▲</button>
                      <button onClick={() => moveFolder(key, 'down')} className="px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-600 dark:text-white rounded">▼</button>
                    </div>
                    <div className="w-40 font-medium dark:text-white">{key}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">priority:</div>
                    <input
                      type="number"
                      value={v.priority || 0}
                      onChange={(e) => handlePriorityChange(key, e.target.value)}
                      className="w-16 px-2 py-1 border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={v.active !== false}
                        onChange={() => handleToggleActive(key)}
                      />
                      <span className="text-sm text-gray-600 dark:text-gray-400">active</span>
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-medium dark:text-white">Workspace & Actions</h3>
            <div className="mt-2 border rounded bg-gray-50 p-3 dark:bg-gray-800 dark:border-gray-700">
              <div className="mb-3">
                <div className="text-sm text-gray-600 dark:text-gray-400">Workspace root</div>
                <input
                  className="w-full mt-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  value={config.workspace_root || ''}
                  onChange={(e) => setConfig({ ...config, workspace_root: e.target.value })}
                />
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleCreateFolders}
                  disabled={creating}
                  className="px-4 py-2 bg-purple-600 text-white rounded disabled:opacity-50"
                >
                  Create configured folders
                </button>
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(JSON.stringify(config, null, 2));
                    alert('Config copied to clipboard');
                  }}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-600 dark:text-white rounded"
                >
                  Copy JSON
                </button>
                <button
                  onClick={async () => {
                    if (!confirm('Force save config (this may overwrite workspace_root or folders). Continue?')) return;
                    try {
                      await saveConfig({ ...config, _force_save: true });
                      alert('Force-saved config');
                    } catch (e) {
                      alert('Force save failed: ' + e.message);
                    }
                  }}
                  className="px-4 py-2 bg-red-500 text-white rounded"
                >
                  Force Save
                </button>
              </div>

              {creating && <div className="mt-3 text-sm text-gray-500 dark:text-gray-400">Creating folders...</div>}
              {createdFolders.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-sm font-medium dark:text-white">Created folders</h4>
                  <ul className="text-sm mt-1 list-disc list-inside dark:text-gray-300">
                    {createdFolders.map((f) => <li key={f}>{f}</li>)}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}