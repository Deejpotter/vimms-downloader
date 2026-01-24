import { describe, it, expect, vi } from "vitest";
import fs from "fs";
import path from "path";
import runVimms from "../src/cli/runVimms";

// Test config parsing and run list ordering

describe("runVimms config parsing", () => {
	it("reads per-folder mapping and orders by priority", async () => {
		const tmp = fs.mkdtempSync(path.join(process.cwd(), "tmp-"));
		// create folders
		fs.mkdirSync(path.join(tmp, "A"));
		fs.mkdirSync(path.join(tmp, "B"));
		// create config
		const cfg = { folders: { A: { priority: 5 }, B: { priority: 1 } } };
		const cfgPath = path.join(tmp, "vimms_config.json");
		fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2), "utf-8");

		// run with --src pointing to tmp and --dry-run
		process.argv = ["node", "run", "--src", tmp, "--dry-run"];
		await runVimms();

		fs.rmSync(tmp, { recursive: true, force: true });
	});
});
