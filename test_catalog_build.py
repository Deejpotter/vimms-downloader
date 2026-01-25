"""Test script for remote catalog build endpoint."""
import requests
import time
import json

BASE_URL = 'http://127.0.0.1:8000'

print("=" * 60)
print("Testing Remote Catalog Build Workflow")
print("=" * 60)

# Step 1: Trigger catalog build
print("\n[Step 1] Triggering remote catalog build...")
response = requests.post(
    f'{BASE_URL}/api/catalog/remote/build',
    json={'workspace_root': 'H:/Games'}
)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code != 200:
    print("\n❌ Build trigger failed!")
    exit(1)

print("\n✅ Build started successfully!")

# Step 2: Poll progress
print("\n[Step 2] Polling progress every 5 seconds...")
print("(This will take 15-30 minutes for all consoles)\n")

poll_count = 0
while True:
    time.sleep(5)
    poll_count += 1
    
    response = requests.get(f'{BASE_URL}/api/catalog/remote/progress')
    progress = response.json()
    
    in_progress = progress.get('in_progress', False)
    consoles_done = progress.get('consoles_done', 0)
    consoles_total = progress.get('consoles_total', 0)
    sections_done = progress.get('sections_done', 0)
    sections_total = progress.get('sections_total', 0)
    games_found = progress.get('games_found', 0)
    current_console = progress.get('current_console', 'N/A')
    current_section = progress.get('current_section', 'N/A')
    
    if consoles_total > 0:
        console_pct = (consoles_done / consoles_total) * 100
    else:
        console_pct = 0
    
    if sections_total > 0:
        section_pct = (sections_done / sections_total) * 100
    else:
        section_pct = 0
    
    print(f"[Poll #{poll_count}] Console: {consoles_done}/{consoles_total} ({console_pct:.1f}%) | "
          f"Section: {sections_done}/{sections_total} ({section_pct:.1f}%) | "
          f"Games: {games_found} | Current: {current_console}/{current_section}")
    
    if not in_progress:
        print("\n✅ Build completed!")
        break

# Step 3: Verify catalog file exists
print("\n[Step 3] Checking for catalog file...")
import os
catalog_path = 'c:/Users/Deej/Repos/vimms-downloader/src/webui_remote_catalog.json'
if os.path.exists(catalog_path):
    file_size = os.path.getsize(catalog_path)
    print(f"✅ Catalog file exists: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
else:
    print("❌ Catalog file not found!")

# Step 4: Test GET endpoint
print("\n[Step 4] Testing GET endpoint...")
response = requests.get(f'{BASE_URL}/api/catalog/remote/get')
if response.status_code == 200:
    catalog = response.json()
    consoles = catalog.get('consoles', {})
    total_games = sum(
        len(sections.get('sections', {}).get(section, []))
        for console_data in consoles.values()
        for section in sections.get('sections', {}).keys()
    )
    print(f"✅ Catalog retrieved: {len(consoles)} consoles, ~{total_games} games")
else:
    print(f"❌ GET failed: {response.status_code}")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
