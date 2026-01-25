import { useState, useEffect } from 'react';
import { getSectionGames } from '../services/api';

export function SectionBrowser({ selectedConsole, onGamesLoad }) {
  const [selectedSection, setSelectedSection] = useState(null);
  const [loading, setLoading] = useState(false);

  const sections = selectedConsole?.sections || {};
  const sectionKeys = Object.keys(sections).sort();

  const handleSectionClick = async (section) => {
    if (sections[section] === 0) return; // Don't load empty sections
    
    setSelectedSection(section);
    setLoading(true);

    try {
      const data = await getSectionGames(selectedConsole.key, section);
      onGamesLoad(data.games || []);
    } catch (error) {
      console.error('Failed to load games:', error);
      alert('Failed to load games: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSelectedSection(null);
  }, [selectedConsole]);

  if (!selectedConsole) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">
        Browse {selectedConsole.name} Sections
      </h2>
      <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
        {sectionKeys.map((section) => {
          const count = sections[section];
          const isEmpty = count === 0;
          const isSelected = selectedSection === section;

          return (
            <button
              key={section}
              onClick={() => handleSectionClick(section)}
              disabled={isEmpty || loading}
              className={`
                px-3 py-2 rounded-lg font-medium text-sm transition-all
                ${isSelected
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                  : isEmpty
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 hover:shadow-sm'
                }
              `}
            >
              <div>{section}</div>
              <div className="text-xs opacity-75">{count}</div>
            </button>
          );
        })}
      </div>
      {loading && (
        <div className="mt-4 text-center text-gray-500">
          Loading games...
        </div>
      )}
    </div>
  );
}
