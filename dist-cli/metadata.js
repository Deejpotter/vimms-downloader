"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.parsePopularityFromHtml = parsePopularityFromHtml;
exports.scoreToStars = scoreToStars;
exports.getGamePopularity = getGamePopularity;
function parsePopularityFromHtml(html) {
    const text = html
        .replace(/<[^>]*>/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    // Overall: 8.5 (123 votes)
    let m = /Overall\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*\(?([0-9]+)?\s*votes?\)?/i.exec(text);
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
function scoreToStars(score) {
    const s = Math.max(0, Math.min(10, Number(score)));
    if (s < 2)
        return 1;
    if (s < 4)
        return 2;
    if (s < 6)
        return 3;
    if (s < 8)
        return 4;
    return 5;
}
const metadata_cache_1 = require("./metadata_cache");
async function getGamePopularity(htmlOrUrl, options) {
    const isHtml = /<html/i.test(htmlOrUrl);
    let html = "";
    const ttl = options?.diskCacheTTLMs ?? 24 * 60 * 60 * 1000; // 24h
    if (options?.diskCacheFile && options?.cacheKey) {
        const existing = (0, metadata_cache_1.getCached)(options.diskCacheFile, options.cacheKey, ttl);
        if (existing !== null)
            return existing;
    }
    if (isHtml)
        html = htmlOrUrl;
    else {
        if (options?.cache && options.cache.has(htmlOrUrl))
            return options.cache.get(htmlOrUrl) || null;
        const fetchFn = options?.fetchFn ||
            (async (u) => {
                const res = await fetch(u);
                if (!res.ok)
                    throw new Error("Fetch failed");
                return await res.text();
            });
        try {
            html = await fetchFn(htmlOrUrl);
        }
        catch (e) {
            return null;
        }
    }
    const parsed = parsePopularityFromHtml(html);
    // update caches
    if (parsed && !isHtml && options?.cache)
        options.cache.set(htmlOrUrl, parsed);
    if (options?.diskCacheFile && options?.cacheKey) {
        (0, metadata_cache_1.setCached)(options.diskCacheFile, options.cacheKey, parsed);
    }
    return parsed;
}
