import { useState, useEffect } from 'react';
import { getIndexProgress, getIndex } from '../services/api';

/**
 * Hook to manage index building progress and partial console data
 */
export function useIndexBuilder() {
  const [progress, setProgress] = useState(null);
  const [consoles, setConsoles] = useState([]);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isIncomplete, setIsIncomplete] = useState(false);
  const [isResyncing, setIsResyncing] = useState(false);

  // Load cached index on mount (one-time only)
  useEffect(() => {
    let mounted = true;

    const loadCachedIndex = async () => {
      try {
        const data = await getIndex();
        console.log('Loaded cached index:', data);

        if (mounted && data && data.consoles && data.consoles.length > 0) {
          // Check if index is incomplete
          if (data.complete === false) {
            setIsIncomplete(true);
            console.warn('Index is incomplete - build was interrupted');
          }

          // Transform to match expected format
          const transformed = data.consoles.map(c => ({
            key: c.folder,
            name: c.name,
            folder: c.folder,
            exists: c.exists !== false, // Default to true if not specified
            total_games: Object.values(c.sections || {})
              .reduce((sum, games) => sum + (Array.isArray(games) ? games.length : 0), 0),
            sections: Object.entries(c.sections || {})
              .reduce((acc, [section, games]) => {
                acc[section] = Array.isArray(games) ? games.length : 0;
                return acc;
              }, {})
          }));
          console.log('Transformed consoles:', transformed);
          setConsoles(transformed);
        }
      } catch (error) {
        // No cached index, that's fine - user needs to build it
        console.log('No cached index found:', error.message);
      }
    };

    loadCachedIndex();

    return () => {
      mounted = false;
    };
  }, []);

  // Poll when building OR when incomplete (to catch auto-rebuild)
  useEffect(() => {
    if (!isBuilding && !isIncomplete) return;

    let mounted = true;

    const pollProgress = async () => {
      try {
        const data = await getIndexProgress();
        if (!mounted) return;

        setProgress(data);

        // Update consoles with partial data as it becomes available
        if (data.partial_consoles && data.partial_consoles.length > 0) {
          const transformed = data.partial_consoles.map(c => ({
            key: c.folder,
            name: c.name,
            folder: c.folder,
            exists: c.exists !== false, // Default to true if not specified
            total_games: Object.values(c.sections || {})
              .reduce((sum, games) => sum + (Array.isArray(games) ? games.length : 0), 0),
            sections: Object.entries(c.sections || {})
              .reduce((acc, [section, games]) => {
                acc[section] = Array.isArray(games) ? games.length : 0;
                return acc;
              }, {})
          }));
          setConsoles(transformed);
        }

        // Stop polling when building is complete
        if (!data.in_progress && !data.resync_in_progress) {
          setIsBuilding(false);
          setIsResyncing(false);
          setIsIncomplete(false); // Clear incomplete flag

          // Reload full index after build completes
          try {
            const fullIndex = await getIndex();
            if (mounted && fullIndex && fullIndex.consoles) {
              // Transform the full index like we do on initial load
              const transformed = fullIndex.consoles.map(c => ({
                key: c.folder,
                name: c.name,
                folder: c.folder,
                exists: c.exists !== false,
                total_games: Object.values(c.sections || {})
                  .reduce((sum, games) => sum + (Array.isArray(games) ? games.length : 0), 0),
                sections: Object.entries(c.sections || {})
                  .reduce((acc, [section, games]) => {
                    acc[section] = Array.isArray(games) ? games.length : 0;
                    return acc;
                  }, {})
              }));
              console.log('Build complete - loaded transformed index:', transformed);
              setConsoles(transformed);
            }
          } catch (e) {
            console.error('Failed to load completed index:', e);
          }
        }

        // Handle resync progress
        if (data.resync_in_progress) {
          setIsResyncing(true);
          if (data.resync_partial_consoles && data.resync_partial_consoles.length > 0) {
            const transformed = data.resync_partial_consoles.map(c => ({
              key: c.folder,
              name: c.name,
              folder: c.folder,
              total_games: Object.values(c.sections || {}).reduce((sum, games) => sum + (Array.isArray(games) ? games.length : 0), 0),
              sections: Object.entries(c.sections || {}).reduce((acc, [section, games]) => {
                acc[section] = Array.isArray(games) ? games.length : 0;
                return acc;
              }, {})
            }));
            setConsoles(prev => {
              // Merge partial consoles into existing list (avoid duplicates)
              const byKey = Object.fromEntries(prev.map(p => [p.key, p]));
              transformed.forEach(t => { byKey[t.key] = t });
              return Object.values(byKey);
            });
          }
        }
      } catch (error) {
        console.error('Failed to fetch index progress:', error);
        if (mounted) {
          setIsBuilding(false);
        }
      }
    };

    // Poll immediately, then every 500ms for responsive updates
    pollProgress();
    const interval = setInterval(pollProgress, 500);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [isBuilding, isIncomplete]);

  const startBuild = () => setIsBuilding(true);
  const stopBuild = () => setIsBuilding(false);

  return { progress, consoles, isBuilding, isIncomplete, startBuild, stopBuild };
}
