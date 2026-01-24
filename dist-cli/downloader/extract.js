"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.extractZip = extractZip;
exports.extract7z = extract7z;
const child_process_1 = require("child_process");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
async function extractZip(filePath, outDir) {
    // already using extract-zip in download module; keep here for symmetry
    const extract = (await Promise.resolve().then(() => __importStar(require('extract-zip')))).default;
    await extract(filePath, { dir: outDir });
}
function extract7z(filePath, outDir) {
    return new Promise((resolve, reject) => {
        // Try to use system `7z` executable
        const exe = '7z';
        if (!fs_1.default.existsSync(path_1.default.dirname(filePath)))
            return reject(new Error('file dir missing'));
        const args = ['x', filePath, `-o${outDir}`, '-y'];
        const proc = (0, child_process_1.spawn)(exe, args, { stdio: 'ignore' });
        let called = false;
        proc.on('error', (err) => {
            if (called)
                return;
            called = true;
            reject(err);
        });
        proc.on('close', (code) => {
            if (called)
                return;
            called = true;
            if (code === 0)
                resolve();
            else
                reject(new Error(`7z exited with code ${code}`));
        });
    });
}
exports.default = { extractZip, extract7z };
