import { useState, useEffect } from 'react';
import { getQueue, clearQueue } from '../services/api';

export function QueuePanel() {
  const [queue, setQueue] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  // Only fetch queue when panel is open
  useEffect(() => {
    if (!isOpen) return;

    let mounted = true;

    const fetchQueue = async () => {
      try {
        const data = await getQueue();
        if (mounted) {
          setQueue(data.queue || []);
        }
      } catch (error) {
        console.error('Failed to fetch queue:', error);
      }
    };

    // Fetch immediately when opened
    fetchQueue();
    
    // Poll every 2 seconds while open
    const interval = setInterval(fetchQueue, 2000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [isOpen]);

  const handleClear = async () => {
    if (!confirm('Are you sure you want to clear the queue?')) return;
    
    try {
      await clearQueue();
      setQueue([]);
    } catch (error) {
      console.error('Failed to clear queue:', error);
      alert('Failed to clear queue: ' + error.message);
    }
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-full p-4 shadow-lg hover:shadow-xl transition-all z-50"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold">Queue</span>
          {queue.length > 0 && (
            <span className="bg-white text-purple-600 rounded-full px-2 py-0.5 text-sm font-bold">
              {queue.length}
            </span>
          )}
        </div>
      </button>

      {/* Sidebar panel */}
      {isOpen && (
        <div className="fixed right-0 top-0 bottom-0 w-96 bg-white shadow-2xl z-40 overflow-y-auto">
          <div className="p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Download Queue</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>

            {queue.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No items in queue</p>
            ) : (
              <>
                <button
                  onClick={handleClear}
                  className="w-full mb-4 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all"
                >
                  Clear Queue
                </button>

                <div className="space-y-4">
                  {queue.map((item, idx) => (
                    <div
                      key={idx}
                      className="border border-gray-200 rounded-lg p-4"
                    >
                      <div className="font-medium text-sm mb-2">{item.title}</div>
                      <div className="text-xs text-gray-500 mb-2">
                        {item.console} • {item.size}
                      </div>
                      {item.status === 'downloading' && (
                        <div className="mt-2">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-gradient-to-r from-purple-600 to-indigo-600 h-2 rounded-full transition-all"
                              style={{ width: `${item.progress || 0}%` }}
                            ></div>
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            {item.progress || 0}%
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          className="fixed inset-0 bg-black bg-opacity-30 z-30"
        ></div>
      )}
    </>
  );
}
