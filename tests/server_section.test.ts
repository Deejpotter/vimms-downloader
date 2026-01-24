import { describe, it, expect, beforeAll, afterAll, vi } from "vitest";
import fs from "fs";
import os from "os";
import path from "path";
import request from "supertest";
import app from "../src/server/app";

let server: any;
beforeAll((done) => {
	server = app.listen(4003, done);
});
afterAll((done) => server.close(done));

describe("server section with local presence and popularity", () => {
	it("returns present=true when a matching file exists", async () => {
		const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vimms-"));
		fs.mkdirSync(path.join(tmp, "ROMs"));
		fs.writeFileSync(path.join(tmp, "ROMs", "Game 1.nds"), "x");

		// stub fetchSectionPage to return local fixture
		const fetchMod = await import("../src/downloader_lib/fetch");
		const sectionHtml = fs.readFileSync(
			path.join("archive", "tests", "fixtures", "section_page.html"),
			"utf-8"
		);
		const stub = vi
			.spyOn(fetchMod, "fetchSectionPage" as any)
			.mockImplementation(async () => sectionHtml);

		const res = await request(server)
			.get("/api/section/A")
			.query({ folder: path.join(tmp, "ROMs") });
		expect(res.status).toBe(200);
		expect(res.body.games.length).toBeGreaterThan(0);
		// first game in fixtures is 'Game 1' — should be present
		expect(res.body.games[0].present).toBe(true);

		stub.mockRestore();
		fs.rmSync(tmp, { recursive: true, force: true });
	});

	it("can return popularity when requested", async () => {
		// stub fetchSectionPage and fetchGamePage
		const fetchMod = await import("../src/downloader_lib/fetch");
		const sectionHtml = fs.readFileSync(
			path.join("archive", "tests", "fixtures", "section_page.html"),
			"utf-8"
		);
		const stubSec = vi
			.spyOn(fetchMod, "fetchSectionPage" as any)
			.mockImplementation(async () => sectionHtml);
		const fetchStub = vi
			.spyOn(fetchMod, "fetchGamePage" as any)
			.mockImplementation(
				async (url: string) =>
					"<html><body>Overall: 8.5 (123 votes)</body></html>"
			);

		const res = await request(server)
			.get("/api/section/A")
			.query({ with_popularity: "1" });
		expect(res.status).toBe(200);
		expect(res.body.games.length).toBeGreaterThan(0);
		expect(res.body.games[0].popularity.score).toBeCloseTo(8.5);
		expect(res.body.games[0].popularity.votes).toBe(123);

		fetchStub.mockRestore();
		stubSec.mockRestore();
	});
});
