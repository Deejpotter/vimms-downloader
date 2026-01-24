const DEFAULT_BASE = "http://127.0.0.1:8000";
const BASE = (import.meta.env.VITE_API_BASE as string) || DEFAULT_BASE;

async function getJson(path: string) {
	const res = await fetch(BASE + path);
	if (!res.ok) throw new Error("API error");
	return await res.json();
}

export async function getSections() {
	return await getJson("/api/sections");
}

export async function getSection(sectionId: string, folder?: string) {
	const q = folder ? `?folder=${encodeURIComponent(folder)}` : "";
	return await getJson(`/api/section/${encodeURIComponent(sectionId)}${q}`);
}

export async function getGame(gameId: string, folder?: string) {
	const q = folder ? `?folder=${encodeURIComponent(folder)}` : "";
	return await getJson(`/api/game/${encodeURIComponent(gameId)}${q}`);
}

export async function postQueue(item: any) {
	const res = await fetch(BASE + "/api/queue", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(item),
	});
	if (!res.ok) throw new Error("Queue error");
	return await res.json();
}

export async function getQueue() {
	return await getJson("/api/queue");
}
export async function getProcessed() {
	return await getJson("/api/processed");
}
