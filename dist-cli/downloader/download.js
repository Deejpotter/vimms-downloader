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
exports.downloadGame = downloadGame;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const fetch_1 = require("../downloader_lib/fetch");
const parse_1 = require("../downloader_lib/parse");
const metadata_1 = require("../metadata");
async function downloadGame(downloadDir, game, options) {
    const dlDir = path_1.default.resolve(downloadDir);
    fs_1.default.mkdirSync(dlDir, { recursive: true });
    // fetch page HTML
    let html;
    if (game.page_url) {
        html = await (0, fetch_1.fetchGamePage)(game.page_url);
    }
    else {
        const url = `https://vimm.net/vault/${game.game_id}`;
        html = await (0, fetch_1.fetchGamePage)(url);
    }
    // resolve download URL via form parsing (POST->GET fallback, mirrors)
    const finalUrl = await (0, parse_1.resolveDownloadForm)(html, fetch, game.page_url || `https://vimm.net/vault/${game.game_id}`, game.game_id);
    if (!finalUrl)
        throw new Error("Could not resolve download URL");
    // decide filename (prefer content-disposition, fallback to URL path)
    const urlParts = new URL(finalUrl);
    let filename = path_1.default.basename(urlParts.pathname) || `${game.game_id}.bin`;
    // if filename has query, strip
    filename = filename.split("?")[0];
    const outPath = path_1.default.join(dlDir, filename);
    // stream download with retries
    const { fetchStreamWithRetries } = await Promise.resolve().then(() => __importStar(require("../downloader_lib/fetch")));
    const maxRetries = 3;
    let lastError = null;
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const res = await fetchStreamWithRetries(finalUrl, { method: "GET" }, 3, 500);
            const fileStream = fs_1.default.createWriteStream(outPath);
            await new Promise((resolve, reject) => {
                const reader = res.body;
                reader.pipe(fileStream);
                reader.on("error", reject);
                fileStream.on("finish", () => resolve());
            });
            lastError = null;
            break;
        }
        catch (e) {
            lastError = e;
            await new Promise((r) => setTimeout(r, 500 * Math.pow(2, attempt)));
        }
    }
    if (lastError)
        throw lastError;
    // Optionally categorize by popularity (uses metadata parser)
    if (options?.categorize) {
        const pop = await (0, metadata_1.getGamePopularity)(game.page_url || `https://vimm.net/vault/${game.game_id}`);
        if (pop) {
            const score = pop.score;
            const label = options.categorizeMode === "score"
                ? `score/${Math.round(score)}`
                : `stars/${score >= 8 ? 5 : Math.max(1, Math.ceil(score / 2))}`;
            const dst = path_1.default.join(dlDir, label);
            fs_1.default.mkdirSync(dst, { recursive: true });
            const target = path_1.default.join(dst, path_1.default.basename(outPath));
            fs_1.default.renameSync(outPath, target);
            // Try extracting if it's a supported archive (.zip, .7z)
            const ext = path_1.default.extname(target).toLowerCase();
            if (ext === ".zip" || ext === ".7z") {
                try {
                    const extractDir = path_1.default.join(dst, path_1.default.basename(target, ext));
                    fs_1.default.mkdirSync(extractDir, { recursive: true });
                    if (ext === ".zip") {
                        const { extractZip } = await Promise.resolve().then(() => __importStar(require("./extract")));
                        await extractZip(target, extractDir);
                    }
                    else if (ext === ".7z") {
                        const { extract7z } = await Promise.resolve().then(() => __importStar(require("./extract")));
                        await extract7z(target, extractDir);
                    }
                }
                catch (e) {
                    // if extraction fails, keep file and log
                    console.warn("Extraction failed or not supported:", e);
                }
            }
            return { file: target, popularity: pop };
        }
    }
    // Try extracting if it's a supported archive (.zip, .7z)
    const ext = path_1.default.extname(outPath).toLowerCase();
    if (ext === ".zip" || ext === ".7z") {
        try {
            const extractDir = path_1.default.join(dlDir, path_1.default.basename(outPath, ext));
            fs_1.default.mkdirSync(extractDir, { recursive: true });
            if (ext === ".zip") {
                const { extractZip } = await Promise.resolve().then(() => __importStar(require("./extract")));
                await extractZip(outPath, extractDir);
            }
            else if (ext === ".7z") {
                const { extract7z } = await Promise.resolve().then(() => __importStar(require("./extract")));
                await extract7z(outPath, extractDir);
            }
            return { file: outPath, extractedTo: extractDir };
        }
        catch (e) {
            console.warn("Extraction failed or not supported:", e);
        }
    }
    return { file: outPath };
}
exports.default = { downloadGame };
