"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.cacheFileForFolder = cacheFileForFolder;
exports.readCache = readCache;
exports.writeCache = writeCache;
exports.getCached = getCached;
exports.setCached = setCached;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
function cacheFileForFolder(folder) {
    // prefer ROMs subfolder
    let target = folder;
    const up = folder.toUpperCase();
    if (!up.includes('ROMS')) {
        const roms = path_1.default.join(folder, 'ROMs');
        if (fs_1.default.existsSync(roms) && fs_1.default.statSync(roms).isDirectory())
            target = roms;
    }
    return path_1.default.join(target, 'metadata_cache.json');
}
function readCache(cacheFile) {
    try {
        if (!fs_1.default.existsSync(cacheFile))
            return {};
        const raw = fs_1.default.readFileSync(cacheFile, 'utf-8');
        return JSON.parse(raw);
    }
    catch (e) {
        return {};
    }
}
function writeCache(cacheFile, data) {
    try {
        const dir = path_1.default.dirname(cacheFile);
        fs_1.default.mkdirSync(dir, { recursive: true });
        fs_1.default.writeFileSync(cacheFile, JSON.stringify(data, null, 2), 'utf-8');
    }
    catch (e) {
        // ignore write errors
    }
}
function getCached(cacheFile, key, ttlMs) {
    const data = readCache(cacheFile);
    const ent = data[key];
    if (!ent)
        return null;
    if (Date.now() - ent.ts > ttlMs)
        return null;
    return ent.popularity;
}
function setCached(cacheFile, key, popularity) {
    const data = readCache(cacheFile);
    data[key] = { popularity, ts: Date.now() };
    writeCache(cacheFile, data);
}
exports.default = { cacheFileForFolder, readCache, writeCache, getCached, setCached };
