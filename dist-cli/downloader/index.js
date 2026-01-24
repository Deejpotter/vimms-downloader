"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SECTIONS = exports.VimmsDownloader = void 0;
const fetch_1 = require("../downloader_lib/fetch");
const parse_1 = require("../downloader_lib/parse");
const filenames_1 = require("../utils/filenames");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
class VimmsDownloader {
    constructor(downloadDir, system) {
        Object.defineProperty(this, "downloadDir", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "system", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "localIndex", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        this.downloadDir = downloadDir;
        this.system = system;
    }
    async getGameListFromSection(section) {
        const games = [];
        let page = 1;
        let pagesFetched = 0;
        let lastErr = null;
        while (true) {
            try {
                const html = await (0, fetch_1.fetchSectionPage)(this.system, section, page);
                pagesFetched += 1;
                const pageGames = (0, parse_1.parseGamesFromSection)(html, section);
                if (!pageGames || !pageGames.length)
                    break;
                games.push(...pageGames);
                page += 1;
            }
            catch (e) {
                lastErr = e;
                // Attempt a fallback: fetch raw response without retries for debugging
                try {
                    const url = `${"https://vimm.net"}/vault/?p=list&action=filters&system=${encodeURIComponent(this.system)}&section=${encodeURIComponent(section)}&page=${page}`;
                    const res = await fetch(url);
                    if (res) {
                        const txt = await res.text();
                        // save debug info
                        try {
                            const dbg = await Promise.resolve().then(() => __importStar(require('./debug')));
                            dbg.saveDebugHtml(this.downloadDir, section, page, txt);
                        }
                        catch (e2) { /* ignore */ }
                        lastErr = new Error(`FetchOK_but_parse_mismatch - fetched ${txt.length} bytes`);
                    }
                }
                catch (inner) {
                    try {
                        const dbg = await Promise.resolve().then(() => __importStar(require('./debug')));
                        dbg.saveDebugError(this.downloadDir, section, page, inner);
                    }
                    catch (e2) { }
                }
                break;
            }
        }
        return { games, pagesFetched, error: lastErr };
    }
    _buildLocalIndex() {
        const ext = [
            ".nds",
            ".n64",
            ".z64",
            ".v64",
            ".iso",
            ".bin",
            ".cue",
            ".gba",
            ".gbc",
            ".gb",
            ".smc",
            ".sfc",
            ".nes",
            ".gcm",
            ".wbfs",
            ".ciso",
            ".rvz",
        ];
        const idx = {};
        let total = 0;
        const walk = (dir) => {
            for (const name of fs_1.default.readdirSync(dir)) {
                const p = path_1.default.join(dir, name);
                try {
                    const st = fs_1.default.statSync(p);
                    if (st.isDirectory())
                        walk(p);
                    else if (st.isFile()) {
                        const extn = path_1.default.extname(name).toLowerCase();
                        if (!ext.includes(extn))
                            continue;
                        total += 1;
                        const key = (0, filenames_1.normalizeForMatch)(name);
                        idx[key] = idx[key] || [];
                        idx[key].push(p);
                    }
                }
                catch (err) {
                    // ignore
                }
            }
        };
        if (fs_1.default.existsSync(this.downloadDir))
            walk(this.downloadDir);
        this.localIndex = idx;
        return idx;
    }
    findAllMatchingFiles(name) {
        if (!this.localIndex)
            this._buildLocalIndex();
        const key = (0, filenames_1.normalizeForMatch)(name);
        const exact = this.localIndex[key] || [];
        // also consider substring containment heuristics
        const results = [...exact];
        for (const k of Object.keys(this.localIndex)) {
            if (k.includes(key) || key.includes(k)) {
                for (const p of this.localIndex[k])
                    if (!results.includes(p))
                        results.push(p);
            }
        }
        return results;
    }
    isGamePresent(name) {
        const matches = this.findAllMatchingFiles(name);
        return matches.length > 0;
    }
}
exports.VimmsDownloader = VimmsDownloader;
exports.SECTIONS = [
    "number",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
];
