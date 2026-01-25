import { useState, useEffect } from 'react';
import { buildIndex, refreshIndex } from '../services/api';

const WORKSPACE_KEY = 'vimms_workspace_root';

export function WorkspaceInit({ onBuildStart, onWorkspaceSet, progress, isBuilding }) {
  const [workspaceRoot, setWorkspaceRoot] = useState('');

  // Load workspace root from localStorage on mount
  useEffect(() => {
    const savedWorkspace = localStorage.getItem(WORKSPACE_KEY);
    if (savedWorkspace) {
      setWorkspaceRoot(savedWorkspace);
    }
  }, []);

  const handleBuild = async () => {
    if (!workspaceRoot.trim()) {
      alert('Please enter a workspace root path');
      return;
    }
    try {
      // Start polling BEFORE making the build request
      onBuildStart();
      await buildIndex(workspaceRoot);
      // Save to localStorage on successful build
      localStorage.setItem(WORKSPACE_KEY, workspaceRoot);
      if (onWorkspaceSet) {
        onWorkspaceSet(workspaceRoot);
      }
    } catch (error) {
      console.error('Failed to build index:', error);
      alert('Failed to build index: ' + error.message);
    }
  };

  const handleRefresh = async () => {
    try {
      // Start polling BEFORE making the refresh request
      onBuildStart();
      await refreshIndex();
    } catch (error) {
      console.error('Failed to refresh index:', error);
      alert('Failed to refresh index: ' + error.message);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Workspace Setup</h2>
      
      <div className="flex gap-4 mb-4">
        <input
          type="text"
          value={workspaceRoot}
          onChange={(e) => setWorkspaceRoot(e.target.value)}
          placeholder="Enter workspace root path (e.g., C:\ROMs)"
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          disabled={isBuilding}
        />
        <button
          onClick={handleBuild}
          disabled={isBuilding}
          className="px-6 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {isBuilding ? 'Building...' : 'Initialize Index'}
        </button>
        <button
          onClick={handleRefresh}
          disabled={isBuilding}
          className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          Refresh Index
        </button>
      </div>

      {isBuilding && progress && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>
              Scanning {progress.current_console || '...'} - Section {progress.current_section || '...'}
            </span>
            <span>{progress.percent_complete || 0}% - {progress.total_games || 0} games</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-gradient-to-r from-purple-600 to-indigo-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${progress.percent_complete || 0}%` }}
            ></div>
          </div>
        </div>
      )}
    </div>
  );
}
