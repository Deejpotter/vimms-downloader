import React, { useEffect, useState } from "react";

declare global {
	interface Window {
		electronAPI?: {
			openFolder: () => Promise<string | null>;
		};
	}
}

const App: React.FC = () => {
	const [folder, setFolder] = useState("./ROMs");
	const [sections, setSections] = useState<string[]>([]);
	const [games, setGames] = useState<any[]>([]);
	const [filter, setFilter] = useState("");
	const [sortKey, setSortKey] = useState<"name" | "present">("name");
	const [queue, setQueue] = useState<any[]>([]);
	const [processed, setProcessed] = useState<any[]>([]);
	const [fetchingPopularity, setFetchingPopularity] = useState(false);

	useEffect(() => {
		import("../api")
			.then((api) =>
				api.getSections().then((j) => setSections(j.sections || []))
			)
			.catch(() => setSections([]));
		const poll = setInterval(() => {
			import("../api").then((api) =>
				api.getQueue().then((j) => setQueue(j.queue || []))
			);
			import("../api").then((api) =>
				api.getProcessed().then((j) => setProcessed(j.processed || []))
			);
		}, 3000);
		return () => clearInterval(poll);
	}, []);

	async function init() {
		const res = await fetch("/api/init", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ folder }),
		});
		const j = await res.json();
		if (j.status === "root") {
			if (j.consoles && j.consoles.length)
				setFolder(j.root + "/" + j.consoles[0]);
			return;
		}
	}

	async function pickFolder() {
		const p = await window.electronAPI?.openFolder();
		if (p) setFolder(p);
	}

	async function loadSection(s: string) {
		const r = await fetch(`/api/section/${s}?folder=${encodeURIComponent(folder)}`)
		const j = await r.json()
		setGames(j.games || [])
	}

	async function fetchPopularityForSection(s: string) {
		setFetchingPopularity(true)
		try {
			const r = await fetch(`/api/section/${s}?folder=${encodeURIComponent(folder)}&with_popularity=1`)
			const j = await r.json()
			setGames(j.games || [])
		} finally {
			setFetchingPopularity(false)
		}
	}
	function filteredAndSortedGames() {
		const f = filter.toLowerCase().trim();
		let list = games.filter(
			(g) =>
				!f || g.name.toLowerCase().includes(f) || String(g.game_id).includes(f)
		);
		list = list.sort((a, b) => {
			if (sortKey === "name") return a.name.localeCompare(b.name);
			return Number(b.present) - Number(a.present);
		});
		return list;
	}

	async function showDetails(game: any) {
		try {
			const api = await import("../api");
			const j = await api.getGame(game.game_id, folder);
			alert(JSON.stringify(j, null, 2));
		} catch (e) {
			alert("Could not fetch details");
		}
	}

	async function queueGame(game: any) {
		try {
			const api = await import("../api");
			await api.postQueue({ folder, game });
			const q = await api.getQueue();
			setQueue(q.queue || []);
		} catch (e) {
			alert("Could not queue");
		}
	}

	return (
		<div style={{ padding: 20 }}>
			<h1>Vimms Desktop (Electron) — MVP</h1>
			<div>
				<input
					value={folder}
					onChange={(e) => setFolder(e.target.value)}
					size={60}
				/>
				<button onClick={init}>Init</button>
				<button onClick={pickFolder}>Select folder</button>
			</div>

			<div style={{ marginTop: 20 }}>
				<strong>Sections</strong>
				<div>
				{fetchingPopularity && <span style={{ marginRight: 12 }}>Fetching popularity...</span>}
				{sections.map((s) => (
					<span key={s} style={{ marginRight: 8 }}>
						<button onClick={() => loadSection(s)} style={{ marginRight: 6 }}>{s}</button>
						<button onClick={() => fetchPopularityForSection(s)} title="Fetch popularity" style={{ fontSize: 11 }} disabled={fetchingPopularity}>P</button>
			</div>

			<div style={{ marginTop: 20 }}>
				<h2>Games</h2>
				<div style={{ marginBottom: 8 }}>
					<input
						placeholder="filter by name or id"
						value={filter}
						onChange={(e) => setFilter(e.target.value)}
					/>
					<select
						value={sortKey}
						onChange={(e) => setSortKey(e.target.value as any)}
						style={{ marginLeft: 8 }}
					>
						<option value="name">Sort: Name</option>
						<option value="present">Sort: Present</option>
					</select>
				</div>
				<table>
					<thead>
						<tr>
							<th>Name</th>
							<th>ID</th>
							<th>Present</th>
							<th>Score</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						{filteredAndSortedGames().map((g) => (
							<tr key={g.game_id}>
								<td>{g.name}</td>
								<td>{g.game_id}</td>
								<td>{String(g.present)}</td>
								<td>{g.popularity?.score ?? "-"}</td>
								<td>
									<button
										onClick={() => showDetails(g)}
										style={{ marginRight: 6 }}
									>
										Details
									</button>
									<button onClick={() => queueGame(g)}>Queue</button>
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>

			<div style={{ marginTop: 20, display: "flex", gap: 20 }}>
				<div>
					<h3>Queue</h3>
					<ul>
						{queue.map((q: any, i: number) => (
							<li key={i}>{JSON.stringify(q)}</li>
						))}
					</ul>
				</div>
				<div>
					<h3>Processed</h3>
					<ul>
						{processed.slice(0, 20).map((p: any, i: number) => (
							<li key={i}>
								{p.item?.game?.game_id || p.item?.game_id || "item"}
							</li>
						))}
					</ul>
				</div>
			</div>
		</div>
	);
};

export default App;
