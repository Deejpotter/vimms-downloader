import { addToQueue } from '../services/api';

export function GamesList({ games, processedIds = [] }) {
  const handleAddToQueue = async (game) => {
    try {
      await addToQueue(game);
      alert(`Added "${game.title}" to download queue`);
    } catch (error) {
      console.error('Failed to add to queue:', error);
      alert('Failed to add to queue: ' + error.message);
    }
  };

  if (!games || games.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <p className="text-gray-500 text-center">Select a section to view games</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">Games ({games.length})</h2>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4">Title</th>
              <th className="text-left py-3 px-4">Size</th>
              <th className="text-left py-3 px-4">Format</th>
              <th className="text-right py-3 px-4">Action</th>
            </tr>
          </thead>
          <tbody>
            {games.map((game, idx) => {
              const isProcessed = processedIds.includes(game.id);
              return (
                <tr
                  key={game.id || idx}
                  className={`border-b border-gray-100 ${idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}`}
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      {game.title || game.name}
                      {isProcessed && (
                        <span className="text-green-500" title="Already downloaded">
                          ✓
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-gray-600">{game.size || '-'}</td>
                  <td className="py-3 px-4 text-gray-600">{game.extension || '-'}</td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => handleAddToQueue(game)}
                      disabled={isProcessed}
                      className={`
                        px-4 py-1.5 rounded-lg text-sm font-medium transition-all
                        ${isProcessed
                          ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                          : 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-700 hover:to-indigo-700'
                        }
                      `}
                    >
                      {isProcessed ? 'Downloaded' : 'Add to Queue'}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
