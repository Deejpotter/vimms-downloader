import fs from "fs";
import path from "path";

export function saveDebugHtml(
	folder: string,
	section: string,
	page: number,
	html: string
) {
	try {
		const d = path.join(process.cwd(), "debug");
		fs.mkdirSync(d, { recursive: true });
		const fname = path.join(d, `section_${section}_page_${page}.html`);
		fs.writeFileSync(fname, html, "utf-8");
		return fname;
	} catch (e) {
		return null;
	}
}

export function saveDebugError(
	folder: string,
	section: string,
	page: number,
	err: any
) {
	try {
		const d = path.join(process.cwd(), "debug");
		fs.mkdirSync(d, { recursive: true });
		const fname = path.join(d, `section_${section}_page_${page}.error.txt`);
		fs.writeFileSync(fname, String(err), "utf-8");
		return fname;
	} catch (e) {
		return null;
	}
}

export default { saveDebugHtml, saveDebugError };
