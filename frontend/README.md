# Frontend Development Guide

This directory contains the React + Tailwind CSS frontend for the Vimm's Lair Downloader web interface.

## Tech Stack

- **Build System**: Vite 7.2.5 (rolldown-vite)
- **Framework**: React 19
- **Styling**: Tailwind CSS v3.4.19
- **Package Manager**: Yarn

## Development Workflow

### First-Time Setup

```bash
cd frontend
yarn install
```

### Development Mode (Hot Reload)

Run both the frontend dev server and Flask backend simultaneously:

```bash
# Terminal 1: Start Flask backend
cd c:\Users\Deej\Repos\vimms-downloader
source .venv/Scripts/activate  # or .venv\Scripts\activate on Windows
python src/webapp.py

# Terminal 2: Start Vite dev server
cd frontend
yarn dev
```

- Frontend dev server: http://localhost:5173
- Flask API backend: http://127.0.0.1:8000
- The Vite dev server proxies `/api/*` requests to Flask automatically

### Production Build

```bash
cd frontend
yarn build
```

This builds the React app and outputs to `../src/webui_static/dist`, which Flask serves in production mode.

### Running Production Build

```bash
cd c:\Users\Deej\Repos\vimms-downloader
source .venv/Scripts/activate
python src/webapp.py
```

Visit http://127.0.0.1:8000 to use the app.

## Project Structure

```
frontend/
├── src/
│   ├── components/       # React components
│   │   ├── WorkspaceInit.jsx      # Workspace initialization panel
│   │   ├── ConsoleGrid.jsx        # Console selection grid
│   │   ├── SectionBrowser.jsx     # Section browser (A-Z, 0-9, #)
│   │   ├── GamesList.jsx          # Games table with download buttons
│   │   ├── QueuePanel.jsx         # Floating download queue sidebar
│   │   └── ProcessedList.jsx      # Recent downloads list
│   ├── hooks/
│   │   └── useIndexBuilder.js     # Custom hook for index building progress
│   ├── services/
│   │   └── api.js                 # API client functions
│   ├── App.jsx            # Main app component
│   ├── main.jsx           # React entry point
│   └── index.css          # Tailwind CSS imports
├── vite.config.js         # Vite configuration (proxy, build output)
└── package.json           # Dependencies and scripts
```

## Key Features

### Progressive Updates

The UI updates progressively as the index is built:
- Console buttons appear as they're scanned
- Section counts update in real-time
- Progress bar shows overall completion
- No page refresh needed

### Responsive Design

- Mobile-first Tailwind breakpoints
- Responsive grid layouts for consoles and sections
- Collapsible queue panel
- Touch-friendly buttons

### Component Architecture

- **WorkspaceInit**: Handles workspace initialization and displays progress
- **ConsoleGrid**: Shows available consoles with game counts, auto-selects first
- **SectionBrowser**: Displays sections for selected console, loads games on click
- **GamesList**: Table view of games with "Add to Queue" buttons
- **QueuePanel**: Floating sidebar showing download queue and progress
- **ProcessedList**: Recent downloads with success/failure indicators

## Styling

Theme: Purple gradient (`from-purple-600 to-indigo-600`)

All components use Tailwind utility classes for styling. Key patterns:
- Gradient backgrounds for primary actions
- Gray scale for secondary UI
- Hover and active states for interactivity
- Shadow and rounded corners for depth

## API Integration

All API calls go through `src/services/api.js`. Available endpoints:

- `POST /api/index/build` - Build index for workspace
- `GET /api/index/progress` - Get index building progress
- `GET /api/index/get` - Get current index
- `POST /api/index/refresh` - Refresh index
- `GET /api/games/{console}/{section}` - Get games for section
- `POST /api/queue/add` - Add game to download queue
- `GET /api/queue/get` - Get current queue
- `GET /api/processed/get` - Get processed downloads
- `DELETE /api/queue/clear` - Clear download queue

## Troubleshooting

### Build warnings

Build warnings about unknown at-rules are harmless and can be ignored. These are compatibility messages from Lightning CSS minifier.

### React build not found

If you see "React build not found" error:
```bash
cd frontend
yarn build
```

### API 404 errors in dev mode

Make sure Flask backend is running on port 8000 before starting Vite dev server.

## Future Improvements

- [ ] Add unit tests with Vitest
- [ ] Add E2E tests with Playwright
- [ ] Implement dark mode toggle
- [ ] Add download speed metrics
- [ ] Implement search/filter for games list
