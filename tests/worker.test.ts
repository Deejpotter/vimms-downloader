import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "fs";
import path from "path";
import request from "supertest";
import app from "../src/server/app";

let server: any;
beforeEach(async () => {
	server = app.listen(4002);
	await new Promise<void>((resolve) => server.once("listening", resolve));
});
afterEach(
	async () =>
		await new Promise<void>((resolve) => server.close(() => resolve()))
);

describe("worker integration", () => {
	it("queues item and processes it (mocked download)", async () => {
		// stub downloadGame
		const mod = await import("../src/downloader/download");
		const stub = vi
			.spyOn(mod, "downloadGame" as any)
			.mockImplementation(async (folder: any, game: any, opts: any) => {
				return { file: path.join(folder, "test.bin") };
			});

		const res = await request(server)
			.post("/api/queue")
			.send({
				folder: "./tmp",
				game: { game_id: "1", page_url: "https://vimm.net/vault/1" },
			});
		expect(res.status).toBe(200);
		// wait a bit for worker to process
		await new Promise((r) => setTimeout(r, 1200));
		const proc = await request(server).get("/api/processed");
		expect(proc.body.processed.length).toBeGreaterThan(0);
		stub.mockRestore();
	});
});
