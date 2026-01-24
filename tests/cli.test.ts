import { describe, it, expect, vi } from "vitest";
import fs from "fs";
import path from "path";
import { exec } from "child_process";

// We'll import the module and call main() directly
import runVimms from "../src/cli/runVimms";

describe("runVimms CLI", () => {
	it("runs in dry-run mode and reports queued items (mocked fetch & presence)", async () => {
		// stub fetchSectionPage to return fixture with one game
		const fetchMod = await import("../src/downloader_lib/fetch");
		const sectionHtml = fs.readFileSync(
			path.join("archive", "tests", "fixtures", "section_page.html"),
			"utf-8"
		);
		const stub = vi
			.spyOn(fetchMod, "fetchSectionPage" as any)
			.mockImplementation(async () => sectionHtml);

		// stub VimmsDownloader.isGamePresent to always false
		const dlMod = await import("../src/downloader/index");
		vi.spyOn(
			dlMod.VimmsDownloader.prototype,
			"isGamePresent" as any
		).mockImplementation(() => false);

		// run with dry-run args
		process.argv = ["node", "run", "--folder", "./", "--dry-run"];
		await runVimms();

		stub.mockRestore();
		vi.unstubAllMocks();
	});
});
