import { queueConsole } from '../services/api';

export function ConsoleGrid({ consoles, selectedConsole, onSelectConsole }) {
  const handleQueueConsole = async (e, console) => {
    e.stopPropagation(); // Prevent console selection
    try {
      await queueConsole(console.folder, console.name);
      alert(`✓ Successfully queued entire ${console.name} library for download\n\nThis will download all sections (A-Z, 0-9) using the CLI downloader.\nCheck the Queue panel to monitor progress.`);
    } catch (error) {
      console.error('Failed to queue console:', error);
      alert('❌ Failed to queue console: ' + error.message);
    }
  };

  if (!consoles || consoles.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <p className="text-gray-500 dark:text-gray-400 text-center">No consoles available. Please initialize the index first.</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold dark:text-white mb-4">Select Console</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {consoles.map((console) => {
          const folderExists = console.exists !== false; // Default to true if not specified
          return (
          <div key={console.key} className="relative">
            <button
              onClick={() => onSelectConsole(console)}
              className={`
                w-full relative px-4 py-3 rounded-lg font-medium transition-all
                ${selectedConsole?.key === console.key
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 dark:from-purple-800 dark:to-indigo-900 text-white shadow-lg scale-105'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 hover:shadow-md'
                }
                ${!folderExists ? 'opacity-60 border-2 border-dashed border-orange-400 dark:border-orange-600' : ''}
              `}
            >
              <div className="flex items-center justify-between gap-1">
                <div className="text-sm font-bold">{console.name}</div>
                {!folderExists && (
                  <span className="text-orange-500 dark:text-orange-400" title="Folder not found on disk">⚠</span>
                )}
              </div>
              <div className="text-xs mt-1 opacity-80">
                {console.total_games || 0} games
              </div>
            </button>
            {folderExists && (
              <button
                onClick={(e) => handleQueueConsole(e, console)}
                className="absolute top-1 right-1 w-6 h-6 bg-green-500 hover:bg-green-600 text-white rounded-full text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center justify-center"
                title={`Queue entire ${console.name} library (all sections A-Z)`}
              >
                +
              </button>
            )}
          </div>
          );
        })}
      </div>
    </div>
  );
}
