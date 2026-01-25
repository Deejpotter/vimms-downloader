export function ConsoleGrid({ consoles, selectedConsole, onSelectConsole }) {
  if (!consoles || consoles.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <p className="text-gray-500 text-center">No consoles available. Please initialize the index first.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Select Console</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {consoles.map((console) => (
          <button
            key={console.key}
            onClick={() => onSelectConsole(console)}
            className={`
              relative px-4 py-3 rounded-lg font-medium transition-all
              ${selectedConsole?.key === console.key
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg scale-105'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 hover:shadow-md'
              }
            `}
          >
            <div className="text-sm font-bold">{console.name}</div>
            <div className="text-xs mt-1 opacity-80">
              {console.total_games || 0} games
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
