import { describe, it, expect, beforeAll, afterAll, vi } from "vitest";
import request from "supertest";
import app from "../src/server/app";

let server: any;
beforeAll((done) => {
	server = app.listen(4004, done);
});
afterAll((done) => server.close(done));

describe("ui fetch popularity", () => {
	it("section popularity endpoint returns popularity for games", async () => {
		const fetchMod = await import("../src/downloader_lib/fetch");
		const stubSec = vi
			.spyOn(fetchMod, "fetchSectionPage" as any)
			.mockImplementation(
				async () =>
					'<html><body><table class="rounded centered cellpadding1 hovertable striped"><tr><td><a href="/vault/1">Game 1</a></td></tr></table></body></html>'
			);
		const fetchStub = vi
			.spyOn(fetchMod, "fetchGamePage" as any)
			.mockImplementation(
				async (url: string) =>
					"<html><body>Overall: 9.2 (456 votes)</body></html>"
			);
		// stub global fetch used by getGamePopularity when URL is provided
		const gfetch = vi
			.fn()
			.mockResolvedValue({
				ok: true,
				text: async () => "<html><body>Overall: 9.2 (456 votes)</body></html>",
			});
		vi.stubGlobal("fetch", gfetch as any);
		const res = await request(server)
			.get("/api/section/A")
			.query({ with_popularity: "1" });
		expect(res.status).toBe(200);
		expect(res.body.games[0].popularity.score).toBeCloseTo(9.2);
		vi.unstubAllGlobals();
		fetchStub.mockRestore();
		stubSec.mockRestore();
	});
});
