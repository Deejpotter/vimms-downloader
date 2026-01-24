import { describe, it, expect } from "vitest";
import {
	parsePopularityFromHtml,
	scoreToStars,
	getGamePopularity,
} from "../src/metadata";

const sampleHtml = `
<html><body>
<div>Overall: 8.6 (123 votes)</div>
</body></html>
`;

describe("metadata", () => {
	it("parses popularity from html", () => {
		const parsed = parsePopularityFromHtml(sampleHtml);
		expect(parsed).not.toBeNull();
		expect(parsed!.score).toBeCloseTo(8.6);
		expect(parsed!.votes).toBe(123);
	});

	it("maps score to stars", () => {
		expect(scoreToStars(0)).toBe(1);
		expect(scoreToStars(3.9)).toBe(2);
		expect(scoreToStars(5)).toBe(3);
		expect(scoreToStars(7.9)).toBe(4);
		expect(scoreToStars(9)).toBe(5);
	});

	it("getGamePopularity uses cache", async () => {
		const cache = new Map<string, any>();
		const url = "http://example.com/game";
		const fetchFn = async (u: string) => sampleHtml;
		const res1 = await getGamePopularity(url, { fetchFn, cache });
		expect(res1).not.toBeNull();
		const res2 = await getGamePopularity(url, {
			fetchFn: async () => {
				throw new Error("should not call");
			},
			cache,
		});
		expect(res2).not.toBeNull();
	});

	it("getGamePopularity uses disk cache", async () => {
		const tmp = fs.mkdtempSync(path.join(process.cwd(), "tmp-"));
		const roms = path.join(tmp, "ROMs");
		fs.mkdirSync(roms);
		const cacheFile = path.join(roms, "metadata_cache.json");
		const url = "http://example.com/game2";
		const res1 = await getGamePopularity(url, {
			fetchFn: async () => sampleHtml,
			diskCacheFile: cacheFile,
			cacheKey: url,
		});
		expect(res1).not.toBeNull();
		// second call should use disk cache (fetch throws)
		const res2 = await getGamePopularity(url, {
			fetchFn: async () => {
				throw new Error("should not call");
			},
			diskCacheFile: cacheFile,
			cacheKey: url,
		});
		expect(res2).not.toBeNull();
		fs.rmSync(tmp, { recursive: true, force: true });
	});
});
