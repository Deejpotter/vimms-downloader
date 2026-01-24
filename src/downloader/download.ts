import fs from "fs";
import path from "path";
import { fetchGamePage, fetchSectionPage } from "../downloader_lib/fetch";
import { resolveDownloadForm } from "../downloader_lib/parse";
import { getGamePopularity } from "../metadata";

export type Game = { game_id: string; page_url?: string; name?: string };

export async function downloadGame(
	downloadDir: string,
	game: Game,
	options?: { categorize?: boolean; categorizeMode?: "stars" | "score" }
) {
	const dlDir = path.resolve(downloadDir);
	fs.mkdirSync(dlDir, { recursive: true });

	// fetch page HTML
	let html: string;
	if (game.page_url) {
		html = await fetchGamePage(game.page_url);
	} else {
		const url = `https://vimm.net/vault/${game.game_id}`;
		html = await fetchGamePage(url);
	}

	// resolve download URL via form parsing (POST->GET fallback, mirrors)
	const finalUrl = await resolveDownloadForm(
		html,
		fetch,
		game.page_url || `https://vimm.net/vault/${game.game_id}`,
		game.game_id
	);
	if (!finalUrl) throw new Error("Could not resolve download URL");

	// decide filename (prefer content-disposition, fallback to URL path)
	const urlParts = new URL(finalUrl);
	let filename = path.basename(urlParts.pathname) || `${game.game_id}.bin`;
	// if filename has query, strip
	filename = filename.split("?")[0];
	const outPath = path.join(dlDir, filename);

	// stream download with retries
	const { fetchStreamWithRetries } = await import("../downloader_lib/fetch");
	const maxRetries = 3;
	let lastError: any = null;
	for (let attempt = 1; attempt <= maxRetries; attempt++) {
		try {
			const res = await fetchStreamWithRetries(
				finalUrl,
				{ method: "GET" },
				3,
				500
			);
			const fileStream = fs.createWriteStream(outPath);
			await new Promise<void>((resolve, reject) => {
				const reader = (res as any).body;
				reader.pipe(fileStream);
				reader.on("error", reject);
				fileStream.on("finish", () => resolve());
			});
			lastError = null;
			break;
		} catch (e) {
			lastError = e;
			await new Promise((r) => setTimeout(r, 500 * Math.pow(2, attempt)));
		}
	}
	if (lastError) throw lastError;

	// Optionally categorize by popularity (uses metadata parser)
	if (options?.categorize) {
		const pop = await getGamePopularity(
			game.page_url || `https://vimm.net/vault/${game.game_id}`
		);
		if (pop) {
			const score = pop.score;
			const label =
				options.categorizeMode === "score"
					? `score/${Math.round(score)}`
					: `stars/${score >= 8 ? 5 : Math.max(1, Math.ceil(score / 2))}`;
			const dst = path.join(dlDir, label);
			fs.mkdirSync(dst, { recursive: true });
			const target = path.join(dst, path.basename(outPath));
			fs.renameSync(outPath, target);

			// Try extracting if it's a supported archive (.zip, .7z)
			const ext = path.extname(target).toLowerCase();
			if (ext === ".zip" || ext === ".7z") {
				try {
					const extractDir = path.join(dst, path.basename(target, ext));
					fs.mkdirSync(extractDir, { recursive: true });
					if (ext === ".zip") {
						const { extractZip } = await import("./extract");
						await extractZip(target, extractDir);
					} else if (ext === ".7z") {
						const { extract7z } = await import("./extract");
						await extract7z(target, extractDir);
					}
				} catch (e) {
					// if extraction fails, keep file and log
					console.warn("Extraction failed or not supported:", e);
				}
			}

			return { file: target, popularity: pop };
		}
	}

	// Try extracting if it's a supported archive (.zip, .7z)
	const ext = path.extname(outPath).toLowerCase();
	if (ext === ".zip" || ext === ".7z") {
		try {
			const extractDir = path.join(dlDir, path.basename(outPath, ext));
			fs.mkdirSync(extractDir, { recursive: true });
			if (ext === ".zip") {
				const { extractZip } = await import("./extract");
				await extractZip(outPath, extractDir);
			} else if (ext === ".7z") {
				const { extract7z } = await import("./extract");
				await extract7z(outPath, extractDir);
			}
			return { file: outPath, extractedTo: extractDir };
		} catch (e) {
			console.warn("Extraction failed or not supported:", e);
		}
	}

	return { file: outPath };
}

export default { downloadGame };
