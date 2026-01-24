import { describe, it, expect, vi } from "vitest";
import * as fetchMod from "../src/downloader_lib/fetch";

describe("fetch helpers", () => {
	it("fetchSectionPage calls fetch and returns text", async () => {
		const sample = "<html><body>test</body></html>";
		// Mock global fetch
		const mock = vi
			.fn()
			.mockResolvedValue({ ok: true, text: async () => sample });
		vi.stubGlobal("fetch", mock);
		const html = await fetchMod.fetchSectionPage("DS", "A", 1);
		expect(html).toContain("test");
		vi.unstubAllGlobals();
	});
});
