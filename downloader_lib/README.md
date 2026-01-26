# Downloader Library

**Shared utilities for Vimm's Lair downloader** — used by both CLI tools and web interface.

## Purpose

This package contains core parsing and fetching logic that is **shared across**:

- ✅ CLI tools (`cli/download_vimms.py`, `cli/run_vimms.py`)
- ✅ Web interface (`src/webapp.py`)
- ✅ Unit tests (`tests/`)

## Modules

### `fetch.py`

Network fetching helpers for communicating with Vimm's Lair.

**Functions:**

- `fetch_section_page(session, system, section, page_num)` — Fetch games list from a section
- `fetch_game_page(session, game_page_url)` — Fetch game detail page

**Features:**

- Random user agent rotation
- Proper headers and referers
- SSL verification disabled (Vimm's Lair SSL issues)

### `parse.py`

HTML parsing helpers for extracting data from Vimm's Lair pages.

**Functions:**

- `parse_games_from_section(html_content, section)` — Extract game list from section page
  - Returns: `[{'name': ..., 'game_id': ..., 'page_url': ..., 'section': ..., 'rating': ...}]`
  - Ratings extracted from table column when available
- `parse_game_details(html_content)` — Extract size/format/rating from game detail page
  - Returns: `{'size_bytes': ..., 'size_display': ..., 'extension': ..., 'rating': ...}`
- `resolve_download_form(html_content, game_id)` — Extract download URL and form data
  - Handles POST-based download forms

## Usage Example

```python
from downloader_lib.fetch import fetch_section_page, fetch_game_page
from downloader_lib.parse import parse_games_from_section, resolve_download_form

import requests

session = requests.Session()

# Fetch and parse section page
response = fetch_section_page(session, system='DS', section='A', page_num=1)
games = parse_games_from_section(response.text, section='A')

# Fetch and parse game page
game_response = fetch_game_page(session, games[0]['page_url'])
download_info = resolve_download_form(game_response.text, games[0]['game_id'])
```

## Tests

Unit tests are located in `tests/` (workspace root):

- `tests/test_parsing.py` — Tests for `parse_games_from_section()` and `resolve_download_form()`
- `tests/test_rating_extraction.py` — Tests for rating extraction from section pages

Fixtures are in `downloader_lib/tests/fixtures/`:

- `section.html` — Sample section page HTML for testing

Run tests:

```bash
pytest tests/test_parsing.py -v
pytest tests/test_rating_extraction.py -v
```

## Dependencies

- `requests` — HTTP client
- `beautifulsoup4` — HTML parsing
- `utils.constants` — User agents, file extensions

## Design Principle

This library contains **only shared parsing and fetching logic**. The main downloader class (`VimmsDownloader`) lives in `cli/download_vimms.py` since it's primarily a CLI tool (though used by the web interface via subprocess).
