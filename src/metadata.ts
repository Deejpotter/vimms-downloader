export type Popularity = { score: number; votes: number } | null;

export function parsePopularityFromHtml(html: string): Popularity {
	const text = html
		.replace(/<[^>]*>/g, " ")
		.replace(/\s+/g, " ")
		.trim();
	// Overall: 8.5 (123 votes)
	let m =
		/Overall\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*\(?([0-9]+)?\s*votes?\)?/i.exec(
			text
		);
	if (m) {
		const score = parseFloat(m[1]);
		const votes = m[2] ? parseInt(m[2], 10) : 0;
		return { score, votes };
	}
	m = /Overall\s*:?\s*([0-9]+(?:\.[0-9]+)?)/i.exec(text);
	if (m) {
		return { score: parseFloat(m[1]), votes: 0 };
	}
	m = /Rating\s*:?\s*([0-9]+(?:\.[0-9]+)?)/i.exec(text);
	if (m) {
		return { score: parseFloat(m[1]), votes: 0 };
	}
	return null;
}

export function scoreToStars(score: number): number {
	const s = Math.max(0, Math.min(10, Number(score)));
	if (s < 2) return 1;
	if (s < 4) return 2;
	if (s < 6) return 3;
	if (s < 8) return 4;
	return 5;
}

import { cacheFileForFolder, getCached, setCached } from "./metadata_cache";

export async function getGamePopularity(
	htmlOrUrl: string,
	options?: {
		fetchFn?: (url: string) => Promise<string>;
		cache?: Map<string, Popularity>;
		diskCacheFile?: string;
		diskCacheTTLMs?: number;
		cacheKey?: string; // explicit key to use for disk cache (usually the page URL)
	}
): Promise<Popularity> {
	const isHtml = /<html/i.test(htmlOrUrl);
	let html = "";
	const ttl = options?.diskCacheTTLMs ?? 24 * 60 * 60 * 1000; // 24h
	if (options?.diskCacheFile && options?.cacheKey) {
		const existing = getCached(options.diskCacheFile, options.cacheKey, ttl);
		if (existing !== null) return existing;
	}
	if (isHtml) html = htmlOrUrl;
	else {
		if (options?.cache && options.cache.has(htmlOrUrl))
			return options.cache.get(htmlOrUrl) || null;
		const fetchFn =
			options?.fetchFn ||
			(async (u: string) => {
				const res = await fetch(u);
				if (!res.ok) throw new Error("Fetch failed");
				return await res.text();
			});
		try {
			html = await fetchFn(htmlOrUrl);
		} catch (e) {
			return null;
		}
	}
	const parsed = parsePopularityFromHtml(html);
	// update caches
	if (parsed && !isHtml && options?.cache) options.cache.set(htmlOrUrl, parsed);
	if (options?.diskCacheFile && options?.cacheKey) {
		setCached(options.diskCacheFile, options.cacheKey, parsed);
	}
	return parsed;
}
