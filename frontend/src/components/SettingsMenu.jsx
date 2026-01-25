import { useState, useEffect } from 'react';
import { refreshIndex, buildRemoteCatalog, getRemoteCatalogProgress } from '../services/api';

export default function SettingsMenu() {
  const [open, setOpen] = useState(false);
  const [reinitializing, setReinitializing] = useState(false);
  const [catalogBuilding, setCatalogBuilding] = useState(false);
  const [catalogProgress, setCatalogProgress] = useState(null);

  // Poll for catalog build progress
  useEffect(() => {
    if (!catalogBuilding) return;
    
    const interval = setInterval(async () => {
      try {
        const progress = await getRemoteCatalogProgress();
        setCatalogProgress(progress);
        
        if (!progress.in_progress) {
          setCatalogBuilding(false);
          setCatalogProgress(null);
          alert('Remote catalog build complete! You can now use fast index scans.');
        }
      } catch (error) {
        console.error('Failed to get catalog progress:', error);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [catalogBuilding]);

  const handleReinitialize = async () => {
    if (!confirm('Reinitialize the entire workspace? This will rebuild the index from scratch.')) {
      return;
    }
    
    setReinitializing(true);
    setOpen(false);
    try {
      await refreshIndex();
      // Reload page to restart UI
      window.location.reload();
    } catch (error) {
      console.error('Failed to reinitialize:', error);
      alert('Failed to reinitialize: ' + error.message);
    } finally {
      setReinitializing(false);
    }
  };

  const handleRefreshCatalog = async () => {
    if (!confirm('Refresh remote catalog from Vimm\'s Lair? This takes 15-30 minutes but only needs to be done once.')) {
      return;
    }
    
    setOpen(false);
    setCatalogBuilding(true);
    try {
      // Get workspace root from current index
      const workspaceRoot = localStorage.getItem('workspace_root') || 'H:/Games';
      await buildRemoteCatalog(workspaceRoot);
    } catch (error) {
      console.error('Failed to refresh catalog:', error);
      alert('Failed to refresh catalog: ' + error.message);
      setCatalogBuilding(false);
    }
  };

  return (
    <div className="relative inline-block text-left">
      <div>
        <button 
          onClick={() => setOpen(!open)} 
          className="px-3 py-2 rounded-md bg-white text-gray-700 shadow-sm border border-gray-200 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-100 dark:border-gray-700 dark:hover:bg-gray-700"
          disabled={reinitializing || catalogBuilding}
        >
          {reinitializing ? 'Reinitializing...' : catalogBuilding ? 'Building Catalog...' : 'Settings'}
        </button>
      </div>
      
      {catalogBuilding && catalogProgress && (
        <div className="absolute right-0 mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md shadow-lg border border-blue-200 dark:border-blue-700 text-sm z-50">
          <div className="font-semibold text-blue-900 dark:text-blue-100 mb-1">Building Remote Catalog...</div>
          <div className="text-blue-700 dark:text-blue-200">
            Console: {catalogProgress.consoles_done}/{catalogProgress.consoles_total} 
            ({((catalogProgress.consoles_done / catalogProgress.consoles_total) * 100).toFixed(1)}%)
          </div>
          <div className="text-blue-700 dark:text-blue-200">
            Section: {catalogProgress.sections_done}/{catalogProgress.sections_total}
          </div>
          <div className="text-blue-700 dark:text-blue-200">
            Games found: {catalogProgress.games_found}
          </div>
          <div className="text-xs text-blue-600 dark:text-blue-300 mt-1">
            Current: {catalogProgress.current_console || 'N/A'}
          </div>
        </div>
      )}
      
      {open && (
        <>
          <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black ring-opacity-5 dark:ring-white/10 p-2 z-50">
            <button 
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-200" 
              onClick={() => { setOpen(false); window.dispatchEvent(new CustomEvent('open-admin')); }}
            >
              Admin Panel
            </button>
            <button 
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-200" 
              onClick={() => { setOpen(false); window.dispatchEvent(new CustomEvent('open-resync')); }}
            >
              Resync Workspace
            </button>
            <button 
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-blue-700 dark:text-blue-300 border-t border-gray-200 dark:border-gray-700 mt-1 pt-2" 
              onClick={handleRefreshCatalog}
            >
              Refresh Remote Catalog
            </button>
            <button 
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-200" 
              onClick={handleReinitialize}
            >
              Reinitialize Workspace
            </button>
          </div>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)}></div>
        </>
      )}
    </div>
  );
}