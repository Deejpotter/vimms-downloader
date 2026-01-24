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
Object.defineProperty(exports, "__esModule", { value: true });
exports.fetchSectionPage = fetchSectionPage;
exports.fetchGamePage = fetchGamePage;
exports.fetchTextWithRetries = fetchTextWithRetries;
exports.fetchStreamWithRetries = fetchStreamWithRetries;
const constants_1 = require("../utils/constants");
const BASE_URL = "https://vimm.net";
const VAULT_BASE = `${BASE_URL}/vault`;
function getRandomUserAgent() {
    return constants_1.USER_AGENTS[Math.floor(Math.random() * constants_1.USER_AGENTS.length)];
}
async function fetchTextWithRetries(url, opts = {}, retries = 3, backoffMs = 300) {
    let lastErr = null;
    for (let i = 0; i < retries; i++) {
        try {
            const res = await fetch(url, opts);
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.text();
        }
        catch (e) {
            lastErr = e;
            // exponential backoff
            await new Promise((r) => setTimeout(r, backoffMs * Math.pow(2, i)));
        }
    }
    // fallback: try axios for environments where global fetch may fail
    try {
        const axios = (await Promise.resolve().then(() => __importStar(require('axios')))).default;
        const hdrs = (opts && opts.headers) || {};
        const r = await axios.get(url, { headers: hdrs, responseType: 'text', timeout: 10000 });
        return r.data;
    }
    catch (e) {
        throw lastErr || e;
    }
}
async function fetchStreamWithRetries(url, opts = {}, retries = 3, backoffMs = 300) {
    let lastErr = null;
    for (let i = 0; i < retries; i++) {
        try {
            const res = await fetch(url, opts);
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return res;
        }
        catch (e) {
            lastErr = e;
            await new Promise((r) => setTimeout(r, backoffMs * Math.pow(2, i)));
        }
    }
    // fallback to axios streaming
    try {
        const axios = (await Promise.resolve().then(() => __importStar(require('axios')))).default;
        const hdrs = (opts && opts.headers) || {};
        const r = await axios.get(url, { headers: hdrs, responseType: 'stream', timeout: 10000 });
        // normalize to { body: stream }
        return { body: r.data };
    }
    catch (e) {
        throw lastErr || e;
    }
}
async function fetchSectionPage(system, section, pageNum = 1) {
    const sectionUrl = `${VAULT_BASE}/?p=list&action=filters&system=${encodeURIComponent(system)}&section=${encodeURIComponent(section)}&page=${pageNum}`;
    const headers = {
        "User-Agent": getRandomUserAgent(),
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    };
    return await fetchTextWithRetries(sectionUrl, { method: "GET", headers });
}
async function fetchGamePage(gamePageUrl) {
    const headers = {
        "User-Agent": getRandomUserAgent(),
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        Referer: VAULT_BASE,
    };
    return await fetchTextWithRetries(gamePageUrl, { method: "GET", headers });
}
exports.default = { fetchSectionPage, fetchGamePage };
