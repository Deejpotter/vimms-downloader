import fs from "fs";
import path from "path";

export type Popularity = { score: number; votes: number } | null;

export type CacheEntry = { popularity: Popularity; ts: number };

export function cacheFileForFolder(folder: string) {
	// prefer ROMs subfolder
	let target = folder;
	const up = folder.toUpperCase();
	if (!up.includes("ROMS")) {
		const roms = path.join(folder, "ROMs");
		if (fs.existsSync(roms) && fs.statSync(roms).isDirectory()) target = roms;
	}
	return path.join(target, "metadata_cache.json");
}

export function readCache(cacheFile: string): Record<string, CacheEntry> {
	try {
		if (!fs.existsSync(cacheFile)) return {};
		const raw = fs.readFileSync(cacheFile, "utf-8");
		return JSON.parse(raw) as Record<string, CacheEntry>;
	} catch (e) {
		return {};
	}
}

export function writeCache(
	cacheFile: string,
	data: Record<string, CacheEntry>
) {
	try {
		const dir = path.dirname(cacheFile);
		fs.mkdirSync(dir, { recursive: true });
		fs.writeFileSync(cacheFile, JSON.stringify(data, null, 2), "utf-8");
	} catch (e) {
		// ignore write errors
	}
}

export function getCached(
	cacheFile: string,
	key: string,
	ttlMs: number
): Popularity | null {
	const data = readCache(cacheFile);
	const ent = data[key];
	if (!ent) return null;
	if (Date.now() - ent.ts > ttlMs) return null;
	return ent.popularity;
}

export function setCached(
	cacheFile: string,
	key: string,
	popularity: Popularity
) {
	const data = readCache(cacheFile);
	data[key] = { popularity, ts: Date.now() };
	writeCache(cacheFile, data);
}

export default {
	cacheFileForFolder,
	readCache,
	writeCache,
	getCached,
	setCached,
};
