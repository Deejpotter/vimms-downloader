import { USER_AGENTS } from "../utils/constants";

const BASE_URL = "https://vimm.net";
const VAULT_BASE = `${BASE_URL}/vault`;

function getRandomUserAgent(): string {
	return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
}

async function fetchTextWithRetries(
	url: string,
	opts: RequestInit = {},
	retries = 3,
	backoffMs = 300
): Promise<string> {
	let lastErr: any = null;
	for (let i = 0; i < retries; i++) {
		try {
			const res = await fetch(url, opts);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return await res.text();
		} catch (e) {
			lastErr = e;
			// exponential backoff
			await new Promise((r) => setTimeout(r, backoffMs * Math.pow(2, i)));
		}
	}
	// fallback: try axios for environments where global fetch may fail
	try {
		const axios = (await import("axios")).default;
		const hdrs = (opts && (opts as any).headers) || {};
		const r = await axios.get(url, {
			headers: hdrs,
			responseType: "text",
			timeout: 10000,
		});
		return r.data as string;
	} catch (e) {
		throw lastErr || e;
	}
}

async function fetchStreamWithRetries(
	url: string,
	opts: RequestInit = {},
	retries = 3,
	backoffMs = 300
): Promise<any> {
	let lastErr: any = null;
	for (let i = 0; i < retries; i++) {
		try {
			const res = await fetch(url, opts as any);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res;
		} catch (e) {
			lastErr = e;
			await new Promise((r) => setTimeout(r, backoffMs * Math.pow(2, i)));
		}
	}
	// fallback to axios streaming
	try {
		const axios = (await import("axios")).default;
		const hdrs = (opts && (opts as any).headers) || {};
		const r = await axios.get(url, {
			headers: hdrs,
			responseType: "stream",
			timeout: 10000,
		});
		// normalize to { body: stream }
		return { body: r.data };
	} catch (e) {
		throw lastErr || e;
	}
}

export async function fetchSectionPage(
	system: string,
	section: string,
	pageNum = 1
): Promise<string> {
	const sectionUrl = `${VAULT_BASE}/?p=list&action=filters&system=${encodeURIComponent(
		system
	)}&section=${encodeURIComponent(section)}&page=${pageNum}`;
	const headers = {
		"User-Agent": getRandomUserAgent(),
		Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	};
	return await fetchTextWithRetries(sectionUrl, { method: "GET", headers });
}

export async function fetchGamePage(gamePageUrl: string): Promise<string> {
	const headers = {
		"User-Agent": getRandomUserAgent(),
		Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
		Referer: VAULT_BASE,
	};
	return await fetchTextWithRetries(gamePageUrl, { method: "GET", headers });
}

export { fetchTextWithRetries, fetchStreamWithRetries };
export default { fetchSectionPage, fetchGamePage };
