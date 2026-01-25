import { useEffect, useState } from 'react';
import { getConfig, saveConfig, createConfiguredFolders } from '../services/configApi';

export default function AdminPanel({ open, onClose }) {
  const [config, setConfig] = useState(null);
  const [editing, setEditing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createdFolders, setCreatedFolders] = useState([]);

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
    const entries = Object.entries(config.folders);
    const idx = entries.findIndex(([k]) => k === key);
    if (idx < 0) return;
    const newIdx = direction === 'up' ? Math.max(0, idx - 1) : Math.min(entries.length - 1, idx + 1);
    const item = entries.splice(idx, 1)[0];
    entries.splice(newIdx, 0, item);
    const newFolders = Object.fromEntries(entries);
    setConfig(prev => ({ ...prev, folders: newFolders }));
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
      <div className="bg-white rounded-lg p-6 w-96 shadow-lg">Loading config...</div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-3/4 max-w-4xl shadow-lg">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Admin — vimms_config.json</h2>
          <div className="flex items-center gap-2">
            <button onClick={() => onClose()} className="px-3 py-1 rounded bg-gray-100">Close</button>
            {!editing ? (
              <button onClick={() => setEditing(true)} className="px-3 py-1 rounded bg-blue-600 text-white">Edit</button>
            ) : (
              <button onClick={handleSave} className="px-3 py-1 rounded bg-green-600 text-white">Save</button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <h3 className="font-medium">Folders</h3>
            <div className="mt-2 border rounded bg-gray-50 p-3 dark:bg-gray-800">
              {Object.entries(config.folders || {}).map(([key, v]) => (
                <div key={key} className="flex items-center justify-between gap-2 py-2 border-b last:border-b-0">
                  <div className="flex items-center gap-3">
                    <button onClick={() => moveFolder(key, 'up')} className="px-2 py-1 bg-gray-200 rounded">▲</button>
                    <button onClick={() => moveFolder(key, 'down')} className="px-2 py-1 bg-gray-200 rounded">▼</button>
                    <div className="w-40 font-medium">{key}</div>
                    <div className="text-sm text-gray-500">priority:</div>
                    <input type="number" value={v.priority || 0} disabled={!editing} onChange={(e)=>handlePriorityChange(key, e.target.value)} className="w-16 px-2 py-1 border rounded" />
                  </div>
                  <div>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" checked={v.active !== false} disabled={!editing} onChange={()=>handleToggleActive(key)} />
                      <span className="text-sm text-gray-600">active</span>
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-medium">Workspace & Actions</h3>
            <div className="mt-2 border rounded bg-gray-50 p-3 dark:bg-gray-800">
              <div className="mb-3">
                <div className="text-sm text-gray-600">Workspace root</div>
                <input className="w-full mt-1 p-2 border rounded" value={config.workspace_root || ''} onChange={(e)=>setConfig({...config, workspace_root: e.target.value})} />
              </div>

              <div className="flex gap-2">
                <button onClick={handleCreateFolders} disabled={creating} className="px-4 py-2 bg-purple-600 text-white rounded">Create configured folders</button>
                <button onClick={()=>{ navigator.clipboard?.writeText(JSON.stringify(config, null, 2)); alert('Config copied to clipboard');}} className="px-4 py-2 bg-gray-200 rounded">Copy JSON</button>
              </div>

              {creating && <div className="mt-3 text-sm text-gray-500">Creating folders...</div>}
              {createdFolders.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-sm font-medium">Created folders</h4>
                  <ul className="text-sm mt-1 list-disc list-inside">
                    {createdFolders.map((f)=> <li key={f}>{f}</li>)}
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