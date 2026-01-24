import { describe, it, expect, beforeAll, afterAll } from "vitest";
import request from "supertest";
import app from "../src/server/app";

let server: any;
beforeAll((done) => {
	server = app.listen(4001, done);
});
afterAll((done) => server.close(done));

describe("server API", () => {
	it("returns sections", async () => {
		const res = await request(server).get("/api/sections");
		expect(res.status).toBe(200);
		expect(Array.isArray(res.body.sections)).toBe(true);
	});

	it("init returns error without folder", async () => {
		const res = await request(server).post("/api/init").send({});
		expect(res.status).toBe(400);
	});
});
