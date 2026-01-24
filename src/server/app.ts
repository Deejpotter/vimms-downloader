import express from "express";
import fs from "fs";
import path from "path";
import { parseGamesFromSection } from "../downloader_lib/parse";
import { fetchSectionPage, fetchGamePage } from "../downloader_lib/fetch";
import { getGamePopularity } from "../metadata";

const app = express();
app.use(express.json());

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;
const DATA_DIR = path.join(process.cwd(), "src");
const QUEUE_FILE = path.join(DATA_DIR, "webui_queue.json");
const PROCESSED_FILE = path.join(DATA_DIR, "webui_processed.json");

let queue: any[] = [];
let processed: any[] = [];

function loadState() {
	try {
		if (fs.existsSync(QUEUE_FILE))
			queue = JSON.parse(fs.readFileSync(QUEUE_FILE, "utf-8"));
	} catch (e) {
		queue = [];
	}
	try {
		if (fs.existsSync(PROCESSED_FILE))
			processed = JSON.parse(fs.readFileSync(PROCESSED_FILE, "utf-8"));
	} catch (e) {
		processed = [];
	}
}

function saveState() {
	try {
		fs.writeFileSync(QUEUE_FILE, JSON.stringify(queue, null, 2), "utf-8");
	} catch (e) {}
	try {
		fs.writeFileSync(
			PROCESSED_FILE,
			JSON.stringify(processed, null, 2),
			"utf-8"
		);
	} catch (e) {}
}

loadState();

// Simple sections list (same as Python SECTIONS)
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

// Very small console map for `init` detection (port of Python CONSOLE_MAP keys)
export const CONSOLE_KEYS = [
	"DS",
	"NDS",
	"NES",
	"SNES",
	"N64",
	"GC",
	"GAMECUBE",
	"WII",
	"GBA",
	"GBC",
	"GB",
	"PS1",
	"PS2",
	"PS3",
	"PSP",
];

app.get("/api/sections", (req, res) => {
	res.json({ sections: SECTIONS });
});

app.post("/api/init", (req, res) => {
	const folder = req.body.folder;
	if (!folder) return res.status(400).json({ error: "folder required" });
	if (!fs.existsSync(folder))
		return res.status(404).json({ error: "folder not found" });
	try {
		const entries = fs.readdirSync(folder, { withFileTypes: true });
		const consoles = entries
			.filter(
				(e) =>
					e.isDirectory() &&
					CONSOLE_KEYS.some((k) =>
						e.name.toLowerCase().includes(k.toLowerCase())
					)
			)
			.map((e) => e.name);
		if (consoles.length)
			return res.json({ status: "root", root: folder, consoles });
		// otherwise check for ROMs subfolder
		const romsDir = path.join(folder, "ROMs");
		const target =
			fs.existsSync(romsDir) && fs.statSync(romsDir).isDirectory()
				? romsDir
				: folder;
		// (We don't create a full downloader instance yet)
		return res.json({ status: "ok", folder: target });
	} catch (e) {
		return res.status(500).json({ error: "could not read folder" });
	}
});

app.get("/api/section/:section", async (req, res) => {
	const section = req.params.section;
	const folder = req.query.folder as string | undefined;
	const withPopularity =
		req.query.with_popularity === "true" || req.query.with_popularity === "1";
	// try to infer system from folder
	let system = "DS";
	if (folder) {
		const up = folder.toUpperCase();
		if (up.includes("GBA")) system = "GBA";
		else if (up.includes("N64")) system = "N64";
		else if (up.includes("PS1")) system = "PS1";
		else if (up.includes("GC") || up.includes("GAMECUBE")) system = "GameCube";
	}

	try {
		// We fetch the section page(s) and parse games; pagination is handled client-side if needed
		const html = await fetchSectionPage(system, section, 1);
		const games = parseGamesFromSection(html, section);

		// If folder provided, build a local index and annotate presence
		let dl: any = null;
		if (folder) {
			const { VimmsDownloader } = await import("../downloader/index");
			dl = new VimmsDownloader(folder, system);
			dl._buildLocalIndex();
		}

		// Optionally fetch popularity for each game (sequentially to be polite)
		const popCache = new Map<string, any>();
		const annotated = [];
		for (const g of games) {
			let present = false;
			if (dl) {
				const matches = dl.findAllMatchingFiles(g.name);
				present = !!(matches && matches.length);
			}
			let popularity = null;
			if (withPopularity) {
				const url = g.page_url;
				if (url) {
					if (popCache.has(url)) popularity = popCache.get(url);
					else {
						try {
							// use disk-backed cache per folder when available
							const { cacheFileForFolder } = await import("../metadata_cache");
							const cacheFile = folder ? cacheFileForFolder(folder) : undefined;
							const pop = await getGamePopularity(url, {
								cache: new Map(),
								diskCacheFile: cacheFile,
								cacheKey: url,
								diskCacheTTLMs: 24 * 60 * 60 * 1000,
							});
							popularity = pop ? { score: pop.score, votes: pop.votes } : null;
							popCache.set(url, popularity);
						} catch (e) {
							popularity = null;
						}
					}
				}
			}
			annotated.push({ ...g, present, popularity });
		}

		res.json({ games: annotated });
	} catch (e) {
		res.status(500).json({ error: "could not fetch section" });
	}
});

app.get("/api/game/:gameId", async (req, res) => {
	const gameId = req.params.gameId;
	const folder = req.query.folder as string | undefined;
	const url = `https://vimm.net/vault/${gameId}`;
	try {
		const html = await fetchGamePage(url);
		// small title extraction
		const m = /<title>([^<]+)<\/title>/i.exec(html);
		const title = m ? m[1].trim() : "";
		const { cacheFileForFolder } = await import("../metadata_cache");
		const cacheFile = folder ? cacheFileForFolder(folder) : undefined;
		const pop = await getGamePopularity(html, {
			cache: new Map(),
			diskCacheFile: cacheFile,
			cacheKey: url,
		});
		const popObj = pop
			? {
					score: pop.score,
					votes: pop.votes,
					rounded_score: Math.round(pop.score),
			  }
			: null;
		res.json({
			game_id: gameId,
			title,
			popularity: popObj,
			present: false,
			files: [],
		});
	} catch (e) {
		res.status(500).json({ error: "could not fetch game page" });
	}
});

app.get("/api/queue", (req, res) => res.json({ queue }));
app.get("/api/processed", (req, res) => res.json({ processed }));
app.delete("/api/queue", (req, res) => {
	queue = [];
	saveState();
	res.json({ status: "cleared" });
});

// Worker: process queue serially using downloadGame
let workerRunning = false;
async function workerLoop() {
	if (workerRunning) return;
	workerRunning = true;
	while (queue.length) {
		const item = queue.shift();
		if (!item) break;
		const folder = item.folder || ".";
		let success = false;
		try {
			const { downloadGame } = await import("../downloader/download");
			const game = item.game || {
				game_id: item.game_id,
				page_url: item.page_url,
				name: item.name,
			};
			await downloadGame(folder, game, {
				categorize: !!item.categorize,
				categorizeMode: item.categorizeMode,
			});
			success = true;
		} catch (e) {
			success = false;
			console.error("Worker download error:", e);
		}
		const record = {
			folder: item.folder || null,
			item,
			success,
			timestamp: new Date().toISOString(),
		};
		processed.unshift(record);
		if (processed.length > 200) processed.pop();
		saveState();
		await new Promise((r) => setTimeout(r, 1000));
	}
	workerRunning = false;
}

function enqueue(item: any) {
	queue.push(item);
	saveState();
	workerLoop().catch((e) => console.error("Worker loop failed:", e));
}

app.post("/api/queue", (req, res) => {
	const item = req.body;
	enqueue(item);
	res.json({ status: "queued" });
});

if (require.main === module) {
	app.listen(PORT, () =>
		console.log(`Express API listening on http://localhost:${PORT}`)
	);
}

export default app;
