import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import {
	cacheFileForFolder,
	getCached,
	setCached,
} from "../src/metadata_cache";

describe("metadata cache", () => {
	it("set and get cache entries", () => {
		const tmp = fs.mkdtempSync(path.join(process.cwd(), "tmp-"));
		const roms = path.join(tmp, "ROMs");
		fs.mkdirSync(roms);
		const cacheFile = cacheFileForFolder(tmp);
		setCached(cacheFile, "http://a", { score: 5, votes: 10 });
		const val = getCached(cacheFile, "http://a", 1000 * 60 * 60);
		expect(val).not.toBeNull();
		expect(val!.score).toBe(5);
		// TTL expiry
		const expired = getCached(cacheFile, "http://a", -1);
		expect(expired).toBeNull();
		fs.rmSync(tmp, { recursive: true, force: true });
	});
});
