#!/usr/bin/env node
"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const index_1 = require("../downloader/index");
const download_1 = require("../downloader/download");
function usage() {
    console.log('Usage: ts-node src/cli/runVimms.ts --folder <path> [--dry-run] [--section <A|B|...>]');
}
function parseArgs() {
    const argv = process.argv.slice(2);
    const folderIdx = argv.indexOf('--folder');
    const folder = folderIdx === -1 ? null : argv[folderIdx + 1];
    const dryRun = argv.includes('--dry-run');
    const sectionIdx = argv.indexOf('--section');
    const section = sectionIdx !== -1 ? argv[sectionIdx + 1] : null;
    const srcIdx = argv.indexOf('--src');
    const src = srcIdx !== -1 ? argv[srcIdx + 1] : null;
    const configIdx = argv.indexOf('--config');
    const config = configIdx !== -1 ? argv[configIdx + 1] : null;
    const report = argv.includes('--report');
    const reportFormatIdx = argv.indexOf('--report-format');
    const reportFormat = reportFormatIdx !== -1 ? argv[reportFormatIdx + 1] : null;
    const verbose = argv.includes('--verbose');
    const debug = argv.includes('--debug');
    const sectionPriorityIdx = argv.indexOf('--section-priority');
    const sectionPriority = sectionPriorityIdx !== -1 ? (argv[sectionPriorityIdx + 1] || '').split(',').map(s => s.trim()).filter(Boolean) : null;
    // forwarded flags
    const extractFiles = argv.includes('--extract-files');
    const deleteDuplicates = argv.includes('--delete-duplicates');
    const yesDelete = argv.includes('--yes-delete');
    const prompt = argv.includes('--prompt');
    const noPrompt = argv.includes('--no-prompt');
    return { folder, dryRun, section, src, config, report, reportFormat, verbose, debug, sectionPriority, extractFiles, deleteDuplicates, yesDelete, prompt, noPrompt };
}
async function main() {
    const args = parseArgs();
    if (!args) {
        usage();
        process.exit(1);
    }
    // If --folder provided, resolve that target; otherwise we'll build run_list from config or workspace
    if (args.folder) {
        const folderPath = path_1.default.resolve(args.folder);
        if (!fs_1.default.existsSync(folderPath) || !fs_1.default.statSync(folderPath).isDirectory()) {
            console.error('Folder not found');
            process.exit(1);
        }
        // prefer ROMs subfolder
        const roms = path_1.default.join(folderPath, 'ROMs');
        const target = fs_1.default.existsSync(roms) && fs_1.default.statSync(roms).isDirectory() ? roms : folderPath;
        console.log(`Starting runVimms on folder: ${target}  (dryRun=${args.dryRun})`);
        const dl = new index_1.VimmsDownloader(target, 'UNKNOWN');
        // Determine section ordering: respect --section-priority or default SECTIONS
        let orderedSections = [];
        if (args.sectionPriority && args.sectionPriority.length) {
            for (const s of args.sectionPriority)
                if (index_1.SECTIONS.includes(s) && !orderedSections.includes(s))
                    orderedSections.push(s);
            for (const s of index_1.SECTIONS)
                if (!orderedSections.includes(s))
                    orderedSections.push(s);
        }
        else {
            orderedSections = [...index_1.SECTIONS];
        }
        const sectionsToRun = args.section ? [args.section] : orderedSections;
        // progress tracking
        const progressFile = path_1.default.join(target, 'download_progress.json');
        let progress = { completed: [], failed: [] };
        try {
            if (fs_1.default.existsSync(progressFile))
                progress = JSON.parse(fs_1.default.readFileSync(progressFile, 'utf-8'));
        }
        catch (e) {
            progress = { completed: [], failed: [] };
        }
        // If progress.last_section exists and user did not provide a section priority override, resume from there
        if (!args.section && (!args.sectionPriority || args.sectionPriority.length === 0) && progress.last_section) {
            const startIdx = orderedSections.indexOf(progress.last_section);
            if (startIdx !== -1) {
                const idx = startIdx + 1; // resume at next section
                if (idx < orderedSections.length) {
                    // start from next section
                    orderedSections = orderedSections.slice(idx);
                }
                else {
                    // already completed all known sections
                    orderedSections = [];
                }
            }
        }
        // if sectionsToRun is empty after resume, nothing to do
        if (!sectionsToRun || !sectionsToRun.length) {
            console.log('No sections to process (resume state or empty selection).');
            console.log('runVimms completed');
            return;
        }
        // existing per-folder flow (unchanged)
        for (const s of sectionsToRun) {
            console.log(`\n${"=".repeat(80)}`);
            const secIdx = sectionsToRun.indexOf(s) + 1;
            console.log(`SECTION: ${s} (${secIdx}/${sectionsToRun.length})`);
            console.log(`${"=".repeat(80)}`);
            const res = await dl.getGameListFromSection(s);
            const games = res.games || [];
            if (res.error) {
                console.log(`  ⚠️  Could not fetch section '${s}': ${String(res.error)}`);
                if (args.verbose)
                    console.log(`    pagesFetched=${res.pagesFetched}`);
                continue;
            }
            if (!games || !games.length) {
                console.log(`  No games found in section '${s}', skipping...`);
                if (args.verbose)
                    console.log(`    pagesFetched=${res.pagesFetched}`);
                continue;
            }
            // fast-skip: if every title appears present locally, skip the whole section
            let allPresent = true;
            for (const g of games) {
                if (!dl.isGamePresent(g.name)) {
                    allPresent = false;
                    break;
                }
            }
            if (allPresent) {
                console.log(`  ⏭️  All ${games.length} titles in section '${s}' appear present locally — skipping section`);
                progress.last_section = s;
                fs_1.default.writeFileSync(progressFile, JSON.stringify(progress, null, 2), 'utf-8');
                continue;
            }
            for (let i = 0; i < games.length; i++) {
                const g = games[i];
                const idx = i + 1;
                console.log(`\n[${idx}/${games.length}] in section '${s}'`);
                if (progress.completed.includes(g.game_id)) {
                    if (dl.isGamePresent(g.name)) {
                        console.log(`  ⏭️  Skipping '${g.name}' (already downloaded)`);
                        continue;
                    }
                    else {
                        console.log(`  ⚠️  Previously completed ${g.game_id} not present locally — will re-download`);
                    }
                }
                const present = dl.isGamePresent(g.name);
                if (present) {
                    console.log(`  ⏭️  Skipping '${g.name}' (local file found)`);
                    continue;
                }
                console.log(`Queuing ${g.name} (${g.game_id})`);
                if (args.dryRun) {
                    console.log(`  [DRY] Would download ${g.name} (${g.game_id})`);
                    continue;
                }
                try {
                    const out = await (0, download_1.downloadGame)(target, { game_id: g.game_id, page_url: g.page_url, name: g.name });
                    console.log(`Downloaded: ${out.file}`);
                    if (!progress.completed.includes(g.game_id))
                        progress.completed.push(g.game_id);
                    fs_1.default.writeFileSync(progressFile, JSON.stringify(progress, null, 2), 'utf-8');
                }
                catch (e) {
                    console.error(`Failed to download ${g.game_id}: ${e}`);
                    progress.failed.push({ id: g.game_id, error: String(e) });
                    fs_1.default.writeFileSync(progressFile, JSON.stringify(progress, null, 2), 'utf-8');
                }
                // Update last_section more frequently
                progress.last_section = s;
                fs_1.default.writeFileSync(progressFile, JSON.stringify(progress, null, 2), 'utf-8');
                // polite delay between downloads
                await new Promise(r => setTimeout(r, 1200));
            }
        }
        console.log('runVimms completed');
        return;
    }
    // runtime_root resolution: use args.src or cfg.src or repo root
    let runtimeRoot = process.cwd();
    if (args.src)
        runtimeRoot = path_1.default.resolve(args.src);
    // If --config provided, use that path; else look for vimms_config.json under runtimeRoot
    const cfgPath = args.config ? path_1.default.resolve(args.config) : path_1.default.join(runtimeRoot, 'vimms_config.json');
    let cfg = {};
    try {
        if (fs_1.default.existsSync(cfgPath))
            cfg = JSON.parse(fs_1.default.readFileSync(cfgPath, 'utf-8'));
    }
    catch (e) { /* ignore */ }
    // allow cfg.src to override runtimeRoot when present
    if (!args.src && cfg.src)
        runtimeRoot = path_1.default.resolve(cfg.src);
    const cfgFolders = cfg.folders || {};
    const perFolderMap = {};
    // legacy whitelist/blacklist
    if (typeof cfgFolders === 'object' && (cfgFolders.whitelist || cfgFolders.blacklist)) {
        const wl = cfgFolders.whitelist || [];
        const bl = cfgFolders.blacklist || [];
        for (const name of wl)
            perFolderMap[String(name)] = { active: true };
        for (const name of bl)
            perFolderMap[String(name)] = { active: false };
    }
    else if (typeof cfgFolders === 'object') {
        for (const [k, v] of Object.entries(cfgFolders)) {
            if (k.startsWith('_'))
                continue;
            if (k === 'whitelist' || k === 'blacklist')
                continue;
            perFolderMap[String(k)] = v || {};
        }
    }
    // Discover run list
    const runCandidates = [];
    try {
        const SKIP_FOLDER_NAMES = new Set(['.git', '.github', '.venv', '.pytest_cache', '.vscode', 'tests', '__pycache__', 'scripts', 'dist', 'node_modules']);
        const items = fs_1.default.readdirSync(runtimeRoot, { withFileTypes: true });
        for (const it of items) {
            if (!it.isDirectory())
                continue;
            const name = it.name;
            if (name.startsWith('.') || SKIP_FOLDER_NAMES.has(name))
                continue;
            // apply per-folder active flag if present
            const pf = perFolderMap[name];
            if (pf && pf.active === false)
                continue;
            runCandidates.push(path_1.default.join(runtimeRoot, name));
        }
    }
    catch (e) { /* ignore */ }
    // If per-folder mapping is present, prefer configured folder order/paths
    const runCandidatesResolved = [];
    if (Object.keys(perFolderMap).length) {
        for (const [name, pf] of Object.entries(perFolderMap)) {
            if (pf && pf.active === false)
                continue;
            let p;
            if (pf && pf.path) {
                p = pf.path;
                if (!path_1.default.isAbsolute(p))
                    p = path_1.default.join(runtimeRoot, p);
            }
            else {
                p = path_1.default.join(runtimeRoot, name);
            }
            try {
                if (fs_1.default.existsSync(p) && fs_1.default.statSync(p).isDirectory())
                    runCandidatesResolved.push(p);
            }
            catch (e) { /* ignore */ }
        }
    }
    else {
        runCandidatesResolved.push(...runCandidates);
    }
    // Sort by priority if provided in perFolderMap or defaults
    const defaultPriority = (cfg.defaults && typeof cfg.defaults.folder_priority === 'number') ? cfg.defaults.folder_priority : 1000000;
    runCandidatesResolved.sort((a, b) => {
        const an = path_1.default.basename(a);
        const bn = path_1.default.basename(b);
        const ap = (perFolderMap[an] && typeof perFolderMap[an].priority === 'number') ? perFolderMap[an].priority : defaultPriority;
        const bp = (perFolderMap[bn] && typeof perFolderMap[bn].priority === 'number') ? perFolderMap[bn].priority : defaultPriority;
        if (ap !== bp)
            return ap - bp;
        return an.localeCompare(bn);
    });
    // Run each candidate in order
    for (const folderPath of runCandidatesResolved) {
        console.log(`\nProcessing folder: ${folderPath}`);
        // Build forwarded argv
        const fwd = ['node', 'run', '--folder', folderPath];
        if (args.dryRun)
            fwd.push('--dry-run');
        if (args.verbose)
            fwd.push('--verbose');
        if (args.debug)
            fwd.push('--debug');
        if (args.sectionPriority && args.sectionPriority.length)
            fwd.push('--section-priority', args.sectionPriority.join(','));
        if (args.extractFiles)
            fwd.push('--extract-files');
        if (args.deleteDuplicates)
            fwd.push('--delete-duplicates');
        if (args.yesDelete)
            fwd.push('--yes-delete');
        if (args.prompt)
            fwd.push('--prompt');
        if (args.noPrompt)
            fwd.push('--no-prompt');
        if (args.src)
            fwd.push('--src', args.src);
        if (args.config)
            fwd.push('--config', args.config);
        // call recursively
        process.argv = fwd;
        await main();
    }
}
if (require.main === module) {
    main().catch(e => { console.error('runVimms error', e); process.exit(1); });
}
exports.default = main;
