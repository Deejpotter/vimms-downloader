import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import runVimms from "../src/cli/runVimms";

describe("runner resume behavior", () => {
	it("resumes at next section when last_section present", async () => {
		const tmp = fs.mkdtempSync(path.join(process.cwd(), "tmp-"));
		// create ROMs folder as expected
		const roms = path.join(tmp, "ROMs");
		fs.mkdirSync(roms);
		// Prepare a minimal progress file marking last_section as B
		const progressFile = path.join(roms, "download_progress.json");
		fs.writeFileSync(
			progressFile,
			JSON.stringify({ completed: [], failed: [], last_section: "B" }, null, 2),
			"utf-8"
		);

		// Run runner pointed at ROMs. It should skip sections up to B and start after B
		process.argv = ["node", "run", "--folder", tmp, "--dry-run"];
		await runVimms();

		fs.rmSync(tmp, { recursive: true, force: true });
	});
});
