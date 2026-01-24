import { describe, it, expect, vi } from "vitest";
import fs from "fs";
import path from "path";
import { downloadGame } from "../src/downloader/download";

describe("downloadGame", () => {
	it("downloads file and returns path (mocked fetch)", async () => {
		// prepare temp dir
		const tmp = fs.mkdtempSync(path.join(process.cwd(), "tmp-"));
		// stub fetch for page and actual download
		const pageHtml =
			'<html><body><form id="dl_form" method="post" action="https://dl.vimm.test/download"><input name="mediaId" value="123"></form></body></html>';
		const mockFetch = vi.fn();
		// first call: fetchGamePage -> return HTML
		mockFetch.mockResolvedValueOnce({ ok: true, text: async () => pageHtml });
		// second call: POST returns redirect url (simulate ok with url)
		mockFetch.mockResolvedValueOnce({
			ok: true,
			url: "https://dl.vimm.test/files/test.bin",
			text: async () => "",
		});
		// third call: actual file download - return body as Readable (simulate with Node stream)
		const stream = fs.createReadStream(
			path.join("archive", "tests", "fixtures", "section_page.html")
		);
		const resp = { ok: true, body: stream };
		mockFetch.mockResolvedValueOnce(resp);

		// stub global fetch
		vi.stubGlobal("fetch", mockFetch as any);

		const res = await downloadGame(tmp, {
			game_id: "1",
			page_url: "https://vimm.net/vault/1",
		});
		expect(res.file).toBeTruthy();
		// cleanup
		fs.rmSync(tmp, { recursive: true, force: true });
		vi.unstubAllGlobals();
	});

	it("extracts .7z files using extract7z (mocked)", async () => {
		const tmp = fs.mkdtempSync(path.join(process.cwd(), "tmp-"));
		const pageHtml =
			'<html><body><form id="dl_form" method="post" action="https://dl.vimm.test/download"><input name="mediaId" value="123"></form></body></html>';
		const mockFetch = vi.fn();
		// page html
		mockFetch.mockResolvedValueOnce({ ok: true, text: async () => pageHtml });
		// POST -> redirect to .7z file URL
		mockFetch.mockResolvedValueOnce({
			ok: true,
			url: "https://dl.vimm.test/files/game.7z",
			text: async () => "",
		});
		// actual file stream
		const tmpFile = path.join(tmp, "game.7z");
		fs.writeFileSync(tmpFile, "dummy");
		const stream = fs.createReadStream(tmpFile);
		mockFetch.mockResolvedValueOnce({ ok: true, body: stream });

		vi.stubGlobal("fetch", mockFetch as any);

		// mock extract module
		const extractMock = {
			extract7z: vi.fn(async (file: string, out: string) => {
				fs.mkdirSync(out, { recursive: true });
				fs.writeFileSync(path.join(out, "extracted.bin"), "x");
			}),
			extractZip: vi.fn(),
		};
		vi.mock("../src/downloader/extract", () => extractMock, { virtual: true });

		const res = await downloadGame(tmp, {
			game_id: "1",
			page_url: "https://vimm.net/vault/1",
		});
		expect(res.extractedTo).toBeTruthy();
		// ensure extract7z was called
		expect(extractMock.extract7z).toHaveBeenCalled();

		fs.rmSync(tmp, { recursive: true, force: true });
		vi.unstubAllGlobals();
		vi.unmock("../src/downloader/extract");
	});
});
