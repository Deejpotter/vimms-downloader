import { useState, useEffect } from 'react';
import { WorkspaceInit } from './components/WorkspaceInit';
import { ConsoleGrid } from './components/ConsoleGrid';
import { SectionBrowser } from './components/SectionBrowser';
import { GamesList } from './components/GamesList';
import { QueuePanel } from './components/QueuePanel';
import { ProcessedList } from './components/ProcessedList';
import { useIndexBuilder } from './hooks/useIndexBuilder';
import { getProcessed, getIndex, queueAll } from './services/api';
import { getConfig } from './services/configApi';
import SettingsMenu from './components/SettingsMenu';
import AdminPanel from './components/AdminPanel';

function App() {
  const { progress, consoles, isBuilding, isIncomplete, startBuild } = useIndexBuilder();
  const [selectedConsole, setSelectedConsole] = useState(null);
  const [games, setGames] = useState([]);
  const [processedIds, setProcessedIds] = useState([]);
  const [workspaceRoot, setWorkspaceRoot] = useState('');
  const [hasWorkspace, setHasWorkspace] = useState(false);
  const [isAdminOpen, setIsAdminOpen] = useState(false);

  // Load workspace from localStorage or config on mount
  useEffect(() => {
    const loadWorkspace = async () => {
      let workspace = localStorage.getItem('vimms_workspace_root');
      
      // If not in localStorage, try loading from config
      if (!workspace) {
        try {
          const config = await getConfig();
          workspace = config.workspace_root;
          if (workspace) {
            localStorage.setItem('vimms_workspace_root', workspace);
            console.log('Loaded workspace from config:', workspace);
          }
        } catch (error) {
          console.error('Failed to load config:', error);
        }
      }
      
      if (workspace) {
        setWorkspaceRoot(workspace);
        setHasWorkspace(true);
      }
    };
    
    loadWorkspace();
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

  // Listen for UI events to open admin modal
  useEffect(() => {
    const handler = () => setIsAdminOpen(true);
    window.addEventListener('open-admin', handler);
    return () => window.removeEventListener('open-admin', handler);
  }, []);

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

  const handleQueueAll = async () => {
    if (!workspaceRoot) {
      alert('❌ Workspace root not set. Please initialize the index first.');
      return;
    }
    
    const consoleCount = consoles.length;
    if (!confirm(`Queue all ${consoleCount} console${consoleCount !== 1 ? 's' : ''} for download?\n\nThis will run the same process as "run_vimms.py" and download all games from all consoles in priority order.\n\nThis may take a very long time. Continue?`)) {
      return;
    }
    
    try {
      await queueAll(workspaceRoot);
      alert(`✓ Successfully queued all ${consoleCount} console${consoleCount !== 1 ? 's' : ''} for download\n\nThe CLI script will process each console in priority order.\nCheck the Queue panel to monitor progress.`);
    } catch (error) {
      console.error('Failed to queue all:', error);
      alert('❌ Failed to queue all consoles: ' + error.message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:bg-gradient-to-br dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="bg-gradient-to-r from-purple-600 to-indigo-600 dark:from-purple-800 dark:to-indigo-900 text-white shadow-lg">
        <div className="container mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Vimm's Lair Downloader</h1>
            <p className="text-purple-100 dark:text-purple-200 mt-1">
              {workspaceRoot ? (
                <span>Workspace: <span className="font-semibold">{workspaceRoot}</span></span>
              ) : (
                'Browse and download retro games'
              )}
            </p>
          </div>
          <div className="flex items-center gap-4">
            {workspaceRoot && consoles.length > 0 && (
              <button
                onClick={handleQueueAll}
                className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-medium shadow-md hover:shadow-lg transition-all flex items-center gap-2"
                title={`Download all games from all ${consoles.length} console${consoles.length !== 1 ? 's' : ''} (runs run_vimms.py)`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Queue All ({consoles.length} console{consoles.length !== 1 ? 's' : ''})
              </button>
            )}

            <SettingsMenu />

            {isIncomplete && !isBuilding && (
              <div className="flex items-center gap-2 bg-yellow-500/20 dark:bg-yellow-600/30 px-3 py-2 rounded-lg">
                <svg className="w-5 h-5 text-yellow-300" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-yellow-100 dark:text-yellow-200">Index incomplete - auto-building...</span>
              </div>
            )}
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
              hasConsoles={consoles.length > 0}
            />
          </div>
        ) : (
          /* Show full app interface when consoles are available */
          <>
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

      {/* Admin modal */}
      <AdminPanel open={isAdminOpen} onClose={() => setIsAdminOpen(false)} />
    </div>
  );
}

export default App;
