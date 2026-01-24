#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { getGamePopularity, scoreToStars } from "../metadata";
import { fetchGamePage } from "../downloader_lib/fetch";

function usage() {
	console.log(
		"Usage: node src/scripts/categorizeByPopularity.ts --folder <path> [--apply] [--mode stars|score] [--cache <path>]"
	);
}

async function main() {
	const argv = process.argv.slice(2);
	const folderIdx = argv.indexOf("--folder");
	if (folderIdx === -1) {
		usage();
		process.exit(1);
	}
	const folder = argv[folderIdx + 1];
	const apply = argv.includes("--apply");
	const modeIdx = argv.indexOf("--mode");
	const mode = modeIdx !== -1 ? argv[modeIdx + 1] : "stars";
	const cacheIdx = argv.indexOf("--cache");
	const cachePath =
		cacheIdx !== -1
			? argv[cacheIdx + 1]
			: path.join(folder, "ROMs", "metadata_cache.json");

	const romsDirCandidate = path.join(folder, "ROMs");
	const romsDir = fs.existsSync(romsDirCandidate) ? romsDirCandidate : folder;

	const progressFile = path.join(romsDir, "download_progress.json");
	if (!fs.existsSync(progressFile)) {
		console.error(
			`No progress file found at ${progressFile}; nothing to categorize`
		);
		process.exit(1);
	}

	const progress = JSON.parse(fs.readFileSync(progressFile, "utf-8"));
	const completed: string[] = progress.completed || [];
	const moved: any[] = [];
	const failed: any[] = [];

	for (const gameId of completed) {
		const url = `https://vimm.net/vault/${gameId}`;
		// try to get popularity (cached in memory)
		const html = await fetchGamePage(url);
		const pop = await getGamePopularity(html, { cache: new Map() });
		if (!pop) {
			failed.push([gameId, "no popularity data"]);
			continue;
		}
		const score = pop.score;
		const votes = pop.votes;
		let dstLabel = "";
		if (mode === "score") {
			const bucket = Math.round(score);
			dstLabel = `score/${bucket}`;
		} else {
			const stars = scoreToStars(score);
			dstLabel = `stars/${stars}`;
		}

		// look for local files with the game id in the filename
		const foundFiles: string[] = [];
		function walk(dir: string) {
			for (const name of fs.readdirSync(dir)) {
				const p = path.join(dir, name);
				const st = fs.statSync(p);
				if (st.isDirectory()) walk(p);
				else if (st.isFile()) {
					if (name.includes(String(gameId))) foundFiles.push(p);
				}
			}
		}
		walk(romsDir);

		// fallback: try to find by title
		if (!foundFiles.length) {
			const titleMatch = /<title>([^<]+)<\/title>/i.exec(html);
			const title = titleMatch ? titleMatch[1].trim() : "";
			if (title) {
				// naive title match
				function walk2(dir: string) {
					for (const name of fs.readdirSync(dir)) {
						const p = path.join(dir, name);
						const st = fs.statSync(p);
						if (st.isDirectory()) walk2(p);
						else if (st.isFile()) {
							if (
								name.toLowerCase().includes(title.toLowerCase().split(" ")[0])
							)
								foundFiles.push(p);
						}
					}
				}
				walk2(romsDir);
			}
		}

		if (!foundFiles.length) {
			failed.push([gameId, "no local file found"]);
			continue;
		}

		const dstDir = path.join(romsDir, dstLabel);
		if (!apply) {
			console.log(
				`[DRY] Would move ${foundFiles.length} files -> ${dstDir} (score=${score}, votes=${votes})`
			);
			moved.push([gameId, foundFiles, dstLabel]);
		} else {
			fs.mkdirSync(dstDir, { recursive: true });
			for (const f of foundFiles) {
				const target = path.join(dstDir, path.basename(f));
				try {
					fs.renameSync(f, target);
					moved.push([gameId, [target], dstLabel]);
				} catch (e) {
					failed.push([gameId, String(e)]);
				}
			}
		}
	}

	console.log("\nSummary:");
	console.log(`  Processed: ${completed.length}`);
	console.log(`  Moved (or would move): ${moved.length}`);
	console.log(`  Failed: ${failed.length}`);
}

if (require.main === module)
	main().catch((e) => {
		console.error(e);
		process.exit(1);
	});
