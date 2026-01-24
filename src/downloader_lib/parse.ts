import { parse } from "node-html-parser";
import { URL } from "url";
import { ROM_EXTENSIONS } from "../utils/constants";

const BASE_URL = "https://vimm.net";
const DOWNLOAD_BASE = "https://dl2.vimm.net";

export type GameEntry = {
	name: string;
	page_url: string;
	game_id: string;
	section: string;
};

export function parseGamesFromSection(
	htmlContent: string,
	section: string
): GameEntry[] {
	const root = parse(htmlContent);
	const table = root.querySelector(
		"table.rounded.centered.cellpadding1.hovertable.striped"
	);
	if (!table) return [];
	const rows = table.querySelectorAll("tr");
	const games: GameEntry[] = [];
	rows.forEach((row) => {
		const firstTd = row.querySelector("td");
		if (!firstTd) return;
		const link = firstTd.querySelector("a");
		if (!link) return;
		const name = link.text.trim();
		let href = link.getAttribute("href") || "";
		if (!href) return;
		const gameId = href.split("/").pop() || "";
		const pageUrl = BASE_URL + href;
		games.push({ name, page_url: pageUrl, game_id: gameId, section });
	});
	return games;
}

export async function resolveDownloadForm(
	htmlContent: string,
	fetchFn: (input: RequestInfo, init?: RequestInit) => Promise<Response>,
	gamePageUrl: string,
	gameId: string,
	logger?: any
): Promise<string | null> {
	const root = parse(htmlContent);
	const dlForm =
		root.querySelector("#dl_form") || root.querySelector("form[id=dl_form]");
	let mediaId: string | null = null;

	if (dlForm) {
		const formMethod = (dlForm.getAttribute("method") || "GET").toUpperCase();
		const formAction = (dlForm.getAttribute("action") || "").trim();
		try {
			const inputsInfo: any[] = [];
			dlForm.querySelectorAll("input").forEach((inp) => {
				inputsInfo.push({
					name: inp.getAttribute("name"),
					value: inp.getAttribute("value"),
				});
			});
			if (logger)
				logger.info(
					`Found download form for ${gameId}: method=${formMethod}, action=${formAction}, inputs=${JSON.stringify(
						inputsInfo
					)}`
				);
		} catch (e) {
			if (logger)
				logger.exception?.(`Error logging download form for ${gameId}`);
		}

		const mediaInput =
			dlForm.querySelector("input[name=mediaId]") ||
			dlForm.querySelector("input[name^=mediaId i]");
		if (mediaInput) mediaId = mediaInput.getAttribute("value") || null;

		const action = formAction;
		const params: Record<string, string> = {};
		dlForm.querySelectorAll("input").forEach((inp) => {
			const n = inp.getAttribute("name");
			const v = inp.getAttribute("value");
			if (n && v != null) params[n] = v;
		});
		if (mediaId && !params.mediaId) params.mediaId = mediaId;

		if (action) {
			const actionUrl = new URL(action, BASE_URL + "/");
			const method = (dlForm.getAttribute("method") || "get").toLowerCase();

			if (method === "get") {
				const newQ = new URL(actionUrl.toString());
				Object.keys(params).forEach((k) => newQ.searchParams.set(k, params[k]));
				const out = newQ.toString();
				if (logger)
					logger.info?.(
						`Resolved download URL via form action (GET) for ${gameId}: ${out}`
					);
				return out;
			} else {
				try {
					// Build basic headers
					const baseHeaders: Record<string, string> = {
						Referer: gamePageUrl,
						Accept:
							"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
					};
					const resp = await fetchFn(actionUrl.toString(), {
						method: "POST",
						body: new URLSearchParams(params),
						headers: baseHeaders,
					});
					if (resp && resp.ok && resp.url) {
						if (logger)
							logger.info?.(
								`POST form resolved to URL for ${gameId}: ${resp.url}`
							);
						return resp.url;
					}

					// GET fallback
					const getUrl = new URL(actionUrl.toString());
					Object.keys(params).forEach((k) =>
						getUrl.searchParams.set(k, params[k])
					);
					if (logger)
						logger.warn?.(
							`POST form did not return usable URL for ${gameId} (status=${
								resp.status
							}); trying GET fallback ${getUrl.toString()}`
						);
					try {
						const respGet = await fetchFn(getUrl.toString(), {
							method: "GET",
							headers: baseHeaders,
						});
						if (respGet && respGet.ok) {
							if (logger)
								logger.info?.(
									`GET fallback returned URL for ${gameId}: ${respGet.url}`
								);
							return respGet.url || getUrl.toString();
						}
					} catch (e) {
						if (logger)
							logger.exception?.(
								`GET fallback failed for ${gameId} at ${getUrl.toString()}`
							);
					}

					// Try mirrors
					const mirrors = ["dl3.vimm.net", "dl2.vimm.net", "dl1.vimm.net"];
					const original = actionUrl.host;
					for (const m of mirrors) {
						if (m === original) continue;
						const mirrorUrl = new URL(actionUrl.toString());
						mirrorUrl.host = m;
						Object.keys(params).forEach((k) =>
							mirrorUrl.searchParams.set(k, params[k])
						);
						if (logger)
							logger.info?.(
								`Trying mirror ${mirrorUrl.toString()} for ${gameId}`
							);
						try {
							const r = await fetchFn(mirrorUrl.toString(), {
								method: "GET",
								headers: baseHeaders,
							});
							if (r && r.ok) {
								if (logger)
									logger.info?.(
										`Mirror ${m} returned URL for ${gameId}: ${r.url}`
									);
								return r.url || mirrorUrl.toString();
							}
						} catch (err) {
							if (logger)
								logger.exception?.(`Error trying mirror ${m} for ${gameId}`);
						}
					}

					if (logger)
						logger.warn?.(
							`All form submission attempts failed for ${gameId}; returning GET-like URL ${getUrl.toString()}`
						);
					return getUrl.toString();
				} catch (err) {
					const getUrl = new URL(actionUrl.toString());
					Object.keys(params).forEach((k) =>
						getUrl.searchParams.set(k, params[k])
					);
					if (logger)
						logger.exception?.(
							`POST form submission raised exception for ${gameId}, falling back to GET-like URL: ${getUrl.toString()}`
						);
					return getUrl.toString();
				}
			}
		}
	}

	// Fallbacks if form parsing fails — try anchors
	const candidates: [string, string | null][] = [];
	root.querySelectorAll("a").forEach((a) => {
		const href = a.getAttribute("href");
		if (!href) return;
		if (/mediaId=/i.test(href) || /\.(ciso|rvz|iso|gcm)($|\?)/i.test(href)) {
			const resolved = new URL(href, BASE_URL + "/").toString();
			const text = (a.text || "").toLowerCase();
			let ext: string | null = null;
			if (text.includes(".")) {
				const parts = text.split(".");
				ext = "." + parts[parts.length - 1];
			}
			if (!ext) {
				const m = href.match(/\.(ciso|rvz|iso|gcm)($|\?)/i);
				if (m) ext = m[0].toLowerCase().split("?")[0];
			}
			candidates.push([resolved, ext]);
		}
	});

	if (candidates.length) {
		const pref = [".ciso", ".rvz"];
		for (const p of pref) {
			for (const [url, ext] of candidates) {
				if (ext === p) {
					if (logger)
						logger.info?.(
							`Resolved download URL via preferred anchor for ${gameId}: ${url} (matched ${p})`
						);
					return url;
				}
			}
		}
		if (logger)
			logger.info?.(
				`Resolved download URL via anchor for ${gameId}: ${candidates[0][0]}`
			);
		return candidates[0][0];
	}

	if (!mediaId) {
		const alt = root.querySelector("input[name^=mediaId i]");
		mediaId = alt?.getAttribute("value") || null;
	}
	if (mediaId) {
		const fallback = `${DOWNLOAD_BASE}/?mediaId=${mediaId}`;
		if (logger)
			logger.info?.(
				`Fallback constructed download URL for ${gameId}: ${fallback}`
			);
		return fallback;
	}

	return null;
}
