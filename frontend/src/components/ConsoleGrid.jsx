export function ConsoleGrid({ consoles, selectedConsole, onSelectConsole }) {
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
          <button
            key={console.key}
            onClick={() => onSelectConsole(console)}
            className={`
              relative px-4 py-3 rounded-lg font-medium transition-all
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
          );
        })}
      </div>
    </div>
  );
}
