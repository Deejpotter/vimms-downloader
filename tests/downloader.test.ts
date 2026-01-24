import { describe, it, expect, vi } from "vitest";
import { VimmsDownloader } from "../src/downloader/index";
import fs from "fs";

const fixture = fs.readFileSync(
	"archive/tests/fixtures/section_page.html",
	"utf-8"
);

describe("VimmsDownloader", () => {
	it("getGameListFromSection parses pages until empty", async () => {
		// Mock fetchSectionPage used inside the module
		const fetchMod = await import("../src/downloader_lib/fetch");
		const stub = vi
			.spyOn(fetchMod, "fetchSectionPage" as any)
			.mockImplementation(async (s: any, sec: any, p: number) => {
				if (p === 1) return fixture;
				return "";
			});
		const { VimmsDownloader } = await import("../src/downloader/index");
		const dl = new VimmsDownloader(".", "DS");
		const games = await dl.getGameListFromSection("A");
		expect(games.length).toBe(2);
		stub.mockRestore();
	});
});
