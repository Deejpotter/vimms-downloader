import { describe, it, expect, beforeEach } from "vitest";
import fs from "fs";
import os from "os";
import path from "path";
import { VimmsDownloader } from "../src/downloader/index";

let tmpDir = "";
beforeEach(() => {
	tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "vimms-"));
	fs.mkdirSync(path.join(tmpDir, "ROMs"));
	fs.writeFileSync(path.join(tmpDir, "ROMs", "MY_GAME.nds"), "x");
	fs.writeFileSync(path.join(tmpDir, "ROMs", "MY_GAME (EU).nds"), "x");
});

describe("indexing", () => {
	it("builds index and finds matches", () => {
		const dl = new VimmsDownloader(path.join(tmpDir, "ROMs"), "DS");
		const idx = dl._buildLocalIndex();
		expect(Object.keys(idx).length).toBeGreaterThan(0);
		const matches = dl.findAllMatchingFiles("MY GAME");
		expect(matches.length).toBeGreaterThan(0);
		expect(dl.isGamePresent("MY GAME")).toBeTruthy();
	});
});
