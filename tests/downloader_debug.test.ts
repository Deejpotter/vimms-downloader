import { describe, it, expect, vi } from "vitest";
import fs from "fs";
import path from "path";
import { VimmsDownloader } from "../src/downloader/index";

describe("downloader debug fetch", () => {
	it("saves debug html when fallback fetch returns content", async () => {
		// stub fetchSectionPage to throw
		const dl = new VimmsDownloader(".", "DS");
		// stub global fetch to return some HTML for the fallback
		const gfetch = vi
			.fn()
			.mockResolvedValue({ ok: true, text: async () => "<html>OK</html>" });
		vi.stubGlobal("fetch", gfetch as any);

		const res = await dl.getGameListFromSection("A");
		// as page parse will find no games, it should save debug html file
		const dbgPath = path.join(process.cwd(), "debug", "section_A_page_1.html");
		expect(fs.existsSync(dbgPath)).toBe(true);
		// cleanup
		fs.rmSync(path.join(process.cwd(), "debug"), {
			recursive: true,
			force: true,
		});
		vi.unstubAllGlobals();
	});
});
