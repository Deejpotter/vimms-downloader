import { describe, it, expect } from "vitest";
import { cleanFilename, normalizeForMatch } from "../src/utils/filenames";

describe("filename helpers", () => {
	it("cleans filenames", () => {
		expect(cleanFilename("005 4426__MY_GAME_(EU).nds")).toBe("MY GAME.nds");
	});
	it("normalizes for match", () => {
		expect(normalizeForMatch("My Game (EU) [v1].nds")).toBe("my game");
	});
});
