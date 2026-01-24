import { fetchSectionPage } from "../downloader_lib/fetch";
import { parseGamesFromSection } from "../downloader_lib/parse";

import { normalizeForMatch } from "../utils/filenames";
import fs from "fs";
import path from "path";

export class VimmsDownloader {
	downloadDir: string;
	system: string;
	localIndex: Record<string, string[]> | null = null;

	constructor(downloadDir: string, system: string) {
		this.downloadDir = downloadDir;
		this.system = system;
	}

	async getGameListFromSection(section: string) {
		const games: any[] = [];
		let page = 1;
		let pagesFetched = 0;
		let lastErr: any = null;
		while (true) {
			try {
				const html = await fetchSectionPage(this.system, section, page);
				pagesFetched += 1;
				const pageGames = parseGamesFromSection(html, section);
				if (!pageGames || !pageGames.length) break;
				games.push(...pageGames);
				page += 1;
			} catch (e) {
				lastErr = e;
				// Attempt a fallback: fetch raw response without retries for debugging
				try {
					const url = `${"https://vimm.net"}/vault/?p=list&action=filters&system=${encodeURIComponent(
						this.system
					)}&section=${encodeURIComponent(section)}&page=${page}`;
					const res = await fetch(url);
					if (res) {
						const txt = await res.text();
						// save debug info
						try {
							const dbg = await import("./debug");
							dbg.saveDebugHtml(this.downloadDir, section, page, txt);
						} catch (e2) {
							/* ignore */
						}
						lastErr = new Error(
							`FetchOK_but_parse_mismatch - fetched ${txt.length} bytes`
						);
					}
				} catch (inner) {
					try {
						const dbg = await import("./debug");
						dbg.saveDebugError(this.downloadDir, section, page, inner);
					} catch (e2) {}
				}
				break;
			}
		}
		return { games, pagesFetched, error: lastErr };
	}

	_buildLocalIndex() {
		const ext = [
			".nds",
			".n64",
			".z64",
			".v64",
			".iso",
			".bin",
			".cue",
			".gba",
			".gbc",
			".gb",
			".smc",
			".sfc",
			".nes",
			".gcm",
			".wbfs",
			".ciso",
			".rvz",
		];
		const idx: Record<string, string[]> = {};
		let total = 0;

		const walk = (dir: string) => {
			for (const name of fs.readdirSync(dir)) {
				const p = path.join(dir, name);
				try {
					const st = fs.statSync(p);
					if (st.isDirectory()) walk(p);
					else if (st.isFile()) {
						const extn = path.extname(name).toLowerCase();
						if (!ext.includes(extn)) continue;
						total += 1;
						const key = normalizeForMatch(name);
						idx[key] = idx[key] || [];
						idx[key].push(p);
					}
				} catch (err) {
					// ignore
				}
			}
		};

		if (fs.existsSync(this.downloadDir)) walk(this.downloadDir);
		this.localIndex = idx;
		return idx;
	}

	findAllMatchingFiles(name: string) {
		if (!this.localIndex) this._buildLocalIndex();
		const key = normalizeForMatch(name);
		const exact = this.localIndex![key] || [];
		// also consider substring containment heuristics
		const results = [...exact];
		for (const k of Object.keys(this.localIndex!)) {
			if (k.includes(key) || key.includes(k)) {
				for (const p of this.localIndex![k])
					if (!results.includes(p)) results.push(p);
			}
		}
		return results;
	}

	isGamePresent(name: string) {
		const matches = this.findAllMatchingFiles(name);
		return matches.length > 0;
	}
}

export const SECTIONS = [
	"number",
	"A",
	"B",
	"C",
	"D",
	"E",
	"F",
	"G",
	"H",
	"I",
	"J",
	"K",
	"L",
	"M",
	"N",
	"O",
	"P",
	"Q",
	"R",
	"S",
	"T",
	"U",
	"V",
	"W",
	"X",
	"Y",
	"Z",
];
