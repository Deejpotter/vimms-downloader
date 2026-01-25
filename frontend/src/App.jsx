import { useState, useEffect } from 'react';
import { WorkspaceInit } from './components/WorkspaceInit';
import { ConsoleGrid } from './components/ConsoleGrid';
import { SectionBrowser } from './components/SectionBrowser';
import { GamesList } from './components/GamesList';
import { QueuePanel } from './components/QueuePanel';
import { ProcessedList } from './components/ProcessedList';
import SettingsMenu from './components/SettingsMenu';
import ResyncModal from './components/ResyncModal';
import { useIndexBuilder } from './hooks/useIndexBuilder';
import { getProcessed, getIndex } from './services/api';

function App() {
  const { progress, consoles, isBuilding, isIncomplete, startBuild } = useIndexBuilder();
  const [selectedConsole, setSelectedConsole] = useState(null);
  const [games, setGames] = useState([]);
  const [processedIds, setProcessedIds] = useState([]);
  const [workspaceRoot, setWorkspaceRoot] = useState('');
  const [hasWorkspace, setHasWorkspace] = useState(false);

  // Load workspace from localStorage on mount
  useEffect(() => {
    const savedWorkspace = localStorage.getItem('vimms_workspace_root');
    if (savedWorkspace) {
      setWorkspaceRoot(savedWorkspace);
      setHasWorkspace(true);
    }
  }, []);

  // Update workspace state when index is available
  useEffect(() => {
    if (consoles.length > 0) {
      setHasWorkspace(true);
    }
  }, [consoles]);

  // Auto-select first console when available
  useEffect(() => {
    if (consoles.length > 0 && !selectedConsole) {
      setSelectedConsole(consoles[0]);
    }
  }, [consoles, selectedConsole]);

  // Fetch processed downloads for checkmarks (only when games list changes)
  useEffect(() => {
    if (games.length === 0) return;

    const fetchProcessed = async () => {
      try {
        const data = await getProcessed();
        const ids = (data.processed || []).map(p => p.id).filter(Boolean);
        setProcessedIds(ids);
      } catch (error) {
        console.error('Failed to fetch processed:', error);
      }
    };

    // Fetch once when games load, no polling
    fetchProcessed();
  }, [games]);

  const handleConsoleSelect = (console) => {
    setSelectedConsole(console);
    setGames([]);
  };

  const handleGamesLoad = (loadedGames) => {
    setGames(loadedGames);
  };

  const handleWorkspaceSet = (workspace) => {
    setWorkspaceRoot(workspace);
    setHasWorkspace(true);
    localStorage.setItem('vimms_workspace_root', workspace);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg">
<div className="container mx-auto px-6 py-6 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Vimm's Lair Downloader</h1>
              <p className="text-purple-100 mt-1">Browse and download retro games</p>
            </div>
            <div className="flex items-center gap-4">
              <SettingsMenu />
            </div>
          </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto px-6 py-8">
        {consoles.length === 0 ? (
          /* Show only workspace setup when no consoles are loaded */
          <div className="max-w-2xl mx-auto mt-20">
            <WorkspaceInit
              onBuildStart={startBuild}
              onWorkspaceSet={handleWorkspaceSet}
              progress={progress}
              isBuilding={isBuilding}
            />
          </div>
        ) : (
          /* Show full app interface when consoles are available */
          <>
            {/* Warning banner for incomplete index */}
            {isIncomplete && (
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6 rounded">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-yellow-700">
                      <strong>Incomplete Index:</strong> The previous index build was interrupted. Some consoles may be missing. 
                      Click "Initialize Index" in the workspace setup to rebuild.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <ConsoleGrid
              consoles={consoles}
              selectedConsole={selectedConsole}
              onSelectConsole={handleConsoleSelect}
            />

            {selectedConsole && (
              <SectionBrowser
                selectedConsole={selectedConsole}
                onGamesLoad={handleGamesLoad}
              />
            )}

            <GamesList games={games} processedIds={processedIds} folder={selectedConsole?.folder} />

            <ProcessedList />
          </>
        )}
      </main>

      {/* Floating queue panel - only show when consoles are loaded */}
      {consoles.length > 0 && <QueuePanel />}
    </div>
  );
}

export default App;
