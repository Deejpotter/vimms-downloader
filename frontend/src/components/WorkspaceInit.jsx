import { useState, useEffect } from 'react';
import { buildIndex } from '../services/api';

const WORKSPACE_KEY = 'vimms_workspace_root';

export function WorkspaceInit({ onBuildStart, onWorkspaceSet, progress, isBuilding, hasConsoles }) {
  const [workspaceRoot, setWorkspaceRoot] = useState('');
  const [autoInitialized, setAutoInitialized] = useState(false);

  // Load workspace root from localStorage on mount
  useEffect(() => {
    const savedWorkspace = localStorage.getItem(WORKSPACE_KEY);
    if (savedWorkspace) {
      setWorkspaceRoot(savedWorkspace);
    }
  }, []);

  // Auto-initialize when workspace root is set and no consoles exist yet
  useEffect(() => {
    if (workspaceRoot && !hasConsoles && !isBuilding && !autoInitialized) {
      setAutoInitialized(true);
      handleBuild();
    }
  }, [workspaceRoot, hasConsoles, isBuilding, autoInitialized]);

  const handleBuild = async () => {
    if (!workspaceRoot.trim()) return;
    
    try {
      onBuildStart();
      await buildIndex(workspaceRoot);
      localStorage.setItem(WORKSPACE_KEY, workspaceRoot);
      if (onWorkspaceSet) {
        onWorkspaceSet(workspaceRoot);
      }
    } catch (error) {
      console.error('Failed to build index:', error);
    }
  };

  const handleWorkspaceChange = (value) => {
    setWorkspaceRoot(value);
    setAutoInitialized(false); // Reset flag when user changes workspace
  };

  // Don't show anything if consoles already exist
  if (hasConsoles && !isBuilding) {
    return null;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Workspace Setup</h2>
      
      {isBuilding && !workspaceRoot ? (
        <div className="text-gray-700 dark:text-gray-300 mb-4">
          <p className="flex items-center gap-2">
            <svg className="animate-spin h-5 w-5 text-purple-600 dark:text-purple-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Auto-initializing workspace from configuration...
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            The system is automatically scanning your console folders. This may take a few minutes.
          </p>
        </div>
      ) : (
        <div className="flex gap-4 mb-4">
          <input
            type="text"
            value={workspaceRoot}
            onChange={(e) => handleWorkspaceChange(e.target.value)}
            placeholder="Enter workspace root path (e.g., C:\ROMs)"
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
            disabled={isBuilding}
          />
        </div>
      )}

      {isBuilding && progress && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
            <span>
              Scanning {progress.current_console || '...'} - Section {progress.current_section || '...'}
            </span>
            <span>{progress.percent_complete || 0}% - {progress.total_games || 0} games</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
            <div
              className="bg-gradient-to-r from-purple-600 to-indigo-600 dark:from-purple-800 dark:to-indigo-900 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${progress.percent_complete || 0}%` }}
            ></div>
          </div>
        </div>
      )}

      {!isBuilding && hasConsoles && (
        <div className="mt-2 text-sm text-green-600 dark:text-green-400 flex items-center gap-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          Index ready - {progress?.consoles_found || 0} consoles found
        </div>
      )}
    </div>
  );
}
