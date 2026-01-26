import { useEffect, useState } from 'react';
import { addToQueue } from '../services/api';

export function GamesList({ games, processedIds = [], folder }) {
  const [enriched, setEnriched] = useState([]);

  useEffect(() => {
    // Just use the games as-is - ratings are already in the index
    setEnriched(games || []);
  }, [games]);

  const handleAddToQueue = async (game) => {
    try {
      await addToQueue({ folder, game_id: game.game_id, title: game.name || game.title });
      alert(`Added "${game.title || game.name}" to download queue`);
    } catch (error) {
      console.error('Failed to add to queue:', error);
      alert('Failed to add to queue: ' + error.message);
    }
  };

  if (!games || games.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <p className="text-gray-500 dark:text-gray-400 text-center">Select a section to view games</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold dark:text-white mb-4">Games ({games.length})</h2>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left py-3 px-4 dark:text-gray-300">Title</th>
              <th className="text-left py-3 px-4 dark:text-gray-300">Size</th>
              <th className="text-left py-3 px-4 dark:text-gray-300">Format</th>
              <th className="text-left py-3 px-4 dark:text-gray-300">Rating</th>
              <th className="text-center py-3 px-4 dark:text-gray-300">Downloaded</th>
            </tr>
          </thead>
          <tbody>
            {enriched.map((game, idx) => {
              const idVal = game.game_id || game.id || idx;
              const isProcessed = processedIds.includes(idVal);
              const isPresent = game.present === true; // Explicitly check for true
              const size = game.size_bytes ? `${(game.size_bytes / (1024*1024)).toFixed(2)} MB` : (game.size_bytes === 0 ? '0 B' : '-');
              const ext = game.extension || '-';
              return (
                <tr
                  key={idVal}
                  className={`border-b border-gray-100 dark:border-gray-700 ${idx % 2 === 0 ? 'bg-gray-50 dark:bg-gray-700' : 'bg-white dark:bg-gray-800'}`}
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <div className="font-medium text-sm dark:text-white">{game.title || game.name}</div>
                      {isPresent && (
                        <span className="text-green-500 dark:text-green-400" title="Game files found on disk">
                          ✓
                        </span>
                      )}
                      {isProcessed && !isPresent && (
                        <span className="text-blue-500 dark:text-blue-400" title="Recently downloaded">
                          ↓
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{size}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{ext}</td>
                  <td className="py-3 px-4">
                    {game.rating != null ? (
                      <span className="text-yellow-500 dark:text-yellow-400">{game.rating.toFixed(1)}</span>
                    ) : (
                      <span className="text-gray-400 dark:text-gray-500">—</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {isPresent ? (
                      <span className="text-green-500 dark:text-green-400 text-2xl font-bold" title="Downloaded">✓</span>
                    ) : (
                      <div className="flex items-center justify-center gap-2">
                        <span className="text-red-500 dark:text-red-400 text-2xl font-bold" title="Not downloaded">✗</span>
                        <button
                          onClick={() => handleAddToQueue(game)}
                          disabled={isProcessed}
                          className={`
                            px-3 py-1 rounded-lg text-sm font-medium transition-all
                            ${isProcessed
                              ? 'bg-gray-200 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                              : 'bg-gradient-to-r from-purple-600 to-indigo-600 dark:from-purple-800 dark:to-indigo-900 text-white hover:from-purple-700 hover:to-indigo-700 hover:dark:from-purple-900 hover:dark:to-indigo-900'
                            }
                          `}
                        >
                          {isProcessed ? 'Queued' : 'Download'}
                        </button>
                      </div>
                    )}
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
