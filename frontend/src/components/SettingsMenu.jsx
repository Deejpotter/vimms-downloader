import { useState } from 'react';
import ResyncModal from './ResyncModal';

export default function SettingsMenu() {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative inline-block text-left">
      <div>
        <button onClick={() => setOpen(!open)} className="px-3 py-2 rounded-md bg-white text-gray-700 shadow-sm border border-gray-200 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-100 dark:border-gray-700 dark:hover:bg-gray-700">
          Settings
        </button>
      </div>
      {open && (
        <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 p-2 dark:bg-gray-800 dark:ring-white/10">
          <button className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-200" onClick={() => window.dispatchEvent(new CustomEvent('open-resync'))}>
            Resync Index
          </button>
          <button className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-200" onClick={() => window.dispatchEvent(new CustomEvent('open-admin')) }>
            Admin
          </button>
        </div>
      )}
      <ResyncModal />
    </div>
  );
}