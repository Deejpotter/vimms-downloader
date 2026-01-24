import { describe, it, expect } from "vitest";
import { parseGamesFromSection } from "../src/downloader_lib/parse";
import fs from "fs";

const fixture = fs.readFileSync(
	"archive/tests/fixtures/section_page.html",
	"utf-8"
);

describe("parse", () => {
	it("parses games from section", () => {
		const games = parseGamesFromSection(fixture, "A");
		expect(games.length).toBe(2);
		expect(games[0].name).toBe("Game 1");
		expect(games[0].game_id).toBe("1");
	});
});
