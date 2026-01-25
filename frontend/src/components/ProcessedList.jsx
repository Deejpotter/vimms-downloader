import { useState, useEffect } from 'react';
import { getProcessed } from '../services/api';

export function ProcessedList() {
  const [processed, setProcessed] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  // Fetch once on mount, no polling
  useEffect(() => {
    const fetchProcessed = async () => {
      try {
        const data = await getProcessed();
        setProcessed(data.processed || []);
      } catch (error) {
        console.error('Failed to fetch processed:', error);
      }
    };

    fetchProcessed();
  }, []);

  if (processed.length === 0) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mt-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold dark:text-white">Recent Downloads ({processed.length})</h2>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300"
        >
          {isOpen ? 'Hide' : 'Show'}
        </button>
      </div>

      {isOpen && (
        <div className="space-y-2">
          {processed.slice(0, 10).map((item, idx) => (
            <div
              key={idx}
              className="flex justify-between items-center py-2 px-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
            >
              <div className="flex items-center gap-3">
                {item.success ? (
                  <span className="text-green-500 dark:text-green-400 text-lg">✓</span>
                ) : (
                  <span className="text-red-500 dark:text-red-400 text-lg">✗</span>
                )}
                <div>
                  <div className="font-medium text-sm dark:text-white">{item.title}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">{item.console}</div>
                </div>
              </div>
              <div className="text-xs text-gray-400 dark:text-gray-500">
                {new Date(item.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
