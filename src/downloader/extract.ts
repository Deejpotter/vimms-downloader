import { spawn } from "child_process";
import fs from "fs";
import path from "path";

export async function extractZip(filePath: string, outDir: string) {
	// already using extract-zip in download module; keep here for symmetry
	const extract = (await import("extract-zip")).default;
	await extract(filePath, { dir: outDir });
}

export function extract7z(filePath: string, outDir: string): Promise<void> {
	return new Promise((resolve, reject) => {
		// Try to use system `7z` executable
		const exe = "7z";
		if (!fs.existsSync(path.dirname(filePath)))
			return reject(new Error("file dir missing"));
		const args = ["x", filePath, `-o${outDir}`, "-y"];
		const proc = spawn(exe, args, { stdio: "ignore" });
		let called = false;
		proc.on("error", (err) => {
			if (called) return;
			called = true;
			reject(err);
		});
		proc.on("close", (code) => {
			if (called) return;
			called = true;
			if (code === 0) resolve();
			else reject(new Error(`7z exited with code ${code}`));
		});
	});
}

export default { extractZip, extract7z };
