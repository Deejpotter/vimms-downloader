import { useState, useEffect } from 'react';
import { resyncIndex, getIndex } from '../services/api';

export default function ResyncModal() {
  const [open, setOpen] = useState(false);
  const [missing, setMissing] = useState([]);
  const [missingOnDisk, setMissingOnDisk] = useState([]);
  const [partial, setPartial] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener('open-resync', handler);
    return () => window.removeEventListener('open-resync', handler);
  }, []);

  useEffect(() => {
    if (!open) return;
    // run dry-run resync to learn missing/partial consoles
    (async () => {
      setLoading(true);
      try {
        const data = await resyncIndex({ mode: 'dry' });
        setMissing(data.to_resync || []);
        setMissingOnDisk(data.missing_on_disk || []);
        setPartial(data.partial_in_index || []);
        // Default select all to_resync
        setSelected(new Set(data.to_resync || []));
      } catch (e) {
        console.error('Failed to fetch resync dry-run:', e);
        setMessage('Failed to compute missing consoles: ' + e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [open]);

  const handleToggle = (name) => {
    setSelected(prev => {
      const copy = new Set(prev);
      if (copy.has(name)) copy.delete(name); else copy.add(name);
      return copy;
    });
  };

  const handleResync = async () => {
    if (selected.size === 0) {
      alert('No consoles selected to resync');
      return;
    }
    if (!confirm('Resync will scan selected consoles and update the index. Continue?')) return;
    setLoading(true);
    setMessage('');
    try {
      await resyncIndex({ mode: 'apply', consoles: Array.from(selected) });
      setMessage('Resync started. Progress will appear in the builder progress area.');
      setOpen(false);
      // Notify app to start polling
      window.dispatchEvent(new CustomEvent('start-build'));
    } catch (e) {
      setMessage('Resync failed to start: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-96 shadow-lg">
        <h2 className="text-lg font-semibold mb-4">Resync Index</h2>
        <div className="mb-3 text-sm text-gray-600 dark:text-gray-300">Consoles detected on disk: <span className="font-medium">{missingOnDisk.join(', ') || 'None'}</span></div>
        <div className="mb-3 text-sm text-gray-600 dark:text-gray-300">Partial consoles in index: <span className="font-medium">{partial.join(', ') || 'None'}</span></div>
        <div className="mb-3 text-sm text-gray-600 dark:text-gray-300">Select consoles to resync:</div>
        <div className="max-h-36 overflow-auto mb-4 border rounded p-2 bg-gray-50 dark:bg-gray-800">
          {(missing.concat(partial)).length === 0 && <div className="text-sm text-gray-500">No consoles available to resync</div>}
          {Array.from(new Set(missing.concat(partial))).map((c) => (
            <label key={c} className="flex items-center gap-2 text-sm w-full">
              <input type="checkbox" checked={selected.has(c)} onChange={() => handleToggle(c)} />
              <span className="ml-1">{c}</span>
            </label>
          ))}
        </div>
        <div className="flex gap-2 justify-end">
          <button onClick={() => setOpen(false)} className="px-4 py-2 bg-gray-100 rounded">Close</button>
          <button onClick={() => { /* Dry run already performed on open */ setMessage('Dry run already performed.') }} disabled={loading} className="px-4 py-2 bg-gray-200 rounded">Dry Run</button>
          <button onClick={handleResync} disabled={loading} className="px-4 py-2 bg-purple-600 text-white rounded">Resync</button>
        </div>
        {message && <div className="mt-4 text-sm text-gray-700 dark:text-gray-300">{message}</div>}
      </div>
    </div>
  );
}