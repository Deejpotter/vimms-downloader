"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.saveDebugHtml = saveDebugHtml;
exports.saveDebugError = saveDebugError;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
function saveDebugHtml(folder, section, page, html) {
    try {
        const d = path_1.default.join(process.cwd(), 'debug');
        fs_1.default.mkdirSync(d, { recursive: true });
        const fname = path_1.default.join(d, `section_${section}_page_${page}.html`);
        fs_1.default.writeFileSync(fname, html, 'utf-8');
        return fname;
    }
    catch (e) {
        return null;
    }
}
function saveDebugError(folder, section, page, err) {
    try {
        const d = path_1.default.join(process.cwd(), 'debug');
        fs_1.default.mkdirSync(d, { recursive: true });
        const fname = path_1.default.join(d, `section_${section}_page_${page}.error.txt`);
        fs_1.default.writeFileSync(fname, String(err), 'utf-8');
        return fname;
    }
    catch (e) {
        return null;
    }
}
exports.default = { saveDebugHtml, saveDebugError };
