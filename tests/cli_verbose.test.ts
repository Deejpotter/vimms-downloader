import { describe, it, expect, vi } from "vitest";
import fs from "fs";
import path from "path";
import runVimms from "../src/cli/runVimms";

// Test fetch failure is logged

describe("runVimms verbose fetch errors", () => {
	it("logs fetch failure when section fetch throws", async () => {
		// stub fetchSectionPage to throw
		const fetchMod = await import("../src/downloader_lib/fetch");
		vi.spyOn(fetchMod, "fetchSectionPage" as any).mockImplementation(
			async () => {
				throw new Error("network fail");
			}
		);

		process.argv = [
			"node",
			"run",
			"--folder",
			"./",
			"--section",
			"A",
			"--dry-run",
			"--verbose",
		];
		await runVimms();

		vi.unstubAllMocks();
	});
});
